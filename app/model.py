import os
import logging
from math import ceil
from flask import current_app, session
from iso639 import to_name
import numpy as np
from tensor2tensor.utils import registry, usr_dir, hparam
from tensor2tensor.serving import serving_utils
import sentencepiece as spm
from sentence_splitter import split_text_into_sentences
from websocket import create_connection

from app.dict_utils import get_or_create

log = logging.getLogger(__name__)
usr_dir.import_usr_dir('t2t_usr_dir')
hparams = hparam.HParams(data_dir=os.path.expanduser('t2t_data_dir'))


class Model(object):

    @staticmethod
    def create(cfg):
        if 'model_framework' in cfg:
            if cfg['model_framework'] == 'marian':
                return MarianModel(cfg)
        return T2TModel(cfg)

    @staticmethod
    def lang_list_display(lang_list):
        return ', '.join(map(to_name, lang_list))

    def __init__(self, cfg):
        self.model = cfg['model']
        self.name = self.model
        self.target_to_source = cfg.get('target_to_source', False)

        self.supports = {}
        for src_lang in cfg['source']:
            for tgt_lang in cfg['target']:
                targets = get_or_create(self.supports, src_lang)
                targets.append(tgt_lang)
                if self.target_to_source:
                    targets = get_or_create(self.supports, tgt_lang)
                    targets.append(src_lang)

        if 'sent_chars_limit' in cfg:
            self._sent_chars_limit = cfg['sent_chars_limit']

        if 'server' in cfg:
            self._server = cfg['server']
        self.domain = cfg.get('domain', None)
        self.default = cfg.get('default', False)
        self.prefix_with = cfg.get('prefix_with', None)

        if self.domain:
            ' ({})'.format(self.domain)
        src = Model.lang_list_display(cfg['source'])
        tgt = Model.lang_list_display(cfg['target'])
        arrow = '->'
        if cfg.get('target_to_source', False):
            arrow = '<' + arrow
        self.title = '{name} {domain}({display})' \
            .format(name=cfg['model'],
                    display=cfg.get('display',
                                    '{src}{arrow}{tgt}'.format(src=src, arrow=arrow, tgt=tgt)),
                    domain='- ' + self.domain + ' domain - ' if self.domain else '')

    @property
    def server(self):
        """
        This method needs a valid app context, current_app is not available at init time.
        :return: host:port
        """
        if hasattr(self, '_server'):
            return self._server.format(**current_app.config)
        else:
            return current_app.config['DEFAULT_SERVER']

    @property
    def sent_chars_limit(self):
        """
        This method needs a valid app context, current_app is not available at init time.
        """
        if hasattr(self, '_sent_chars_limit'):
            return self._sent_chars_limit
        else:
            return current_app.config['SENT_LEN_LIMIT']

    def add_href(self, url):
        self.href = url

    def __iter__(self):
        yield 'model', self.model
        yield 'name', self.name
        yield 'supports', self.supports
        yield 'title', self.title
        if self.default:
            yield 'default', self.default
        if self.domain:
            yield 'domain', self.domain
        if self.href:
            yield 'href', self.href

    def translate(self, text, src=None, tgt=None):
        src = src or list(self.supports.keys())[0]
        tgt = tgt or self.supports[src][0]

        sentences, formatting = self.extract_sentences(text, src)
        outputs = self.send_sentences_to_backend(sentences, src, tgt)
        return self.reconstruct_formatting(outputs, formatting)

    def extract_sentences(self, text, text_lang):
        sentences = []
        newlines_after = []
        for segment in text.split('\n'):
            if segment:
                sentences += self.split_to_sent_array(segment, lang=text_lang,
                                                      )
            newlines_after.append(len(sentences) - 1)
        return sentences, newlines_after

    def reconstruct_formatting(self, outputs, newlines_after):
        for i in newlines_after:
            if i >= 0:
                outputs[i] += '\n'
        return outputs


class T2TModel(Model):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.problem = registry.problem(cfg['problem'])
        self.problem.get_hparams(hparams)

    def send_sentences_to_backend(self, sentences, src, tgt):
        if self.prefix_with:
            prefix = self.prefix_with.format(source=src, target=tgt)
        else:
            prefix = ''
        outputs = []
        request_fn = serving_utils.make_grpc_request_fn(servable_name=self.model, timeout_secs=500,
                                                        server=self.server)

        for batch in np.array_split(sentences,
                                    ceil(len(sentences) / current_app.config['BATCH_SIZE'])):
            try:
                outputs += list(map(lambda sent_score: sent_score[0],
                                    serving_utils.predict(
                                        [prefix + sent for sent in batch.tolist()],
                                        self.problem,
                                        request_fn)))
            except:
                # When tensorflow serving restarts web clients seem to "remember" the channel where
                # the connection have failed. clearing up the session, seems to solve that
                session.clear()
                raise
        return outputs

    def split_to_sent_array(self, text, lang):
        charlimit = self.sent_chars_limit
        sent_array = []
        for sent in split_text_into_sentences(text=text, language=lang):
            while len(sent) > charlimit:
                try:
                    # When sent starts with a space, then sent[0:0] was an empty string,
                    # and it caused an infinite loop. This fixes it.
                    beg = 0
                    while sent[beg] == ' ':
                        beg += 1
                    last_space_idx = sent.rindex(" ", beg, charlimit)
                    sent_array.append(sent[0:last_space_idx])
                    sent = sent[last_space_idx:]
                except ValueError:
                    # raised if no space found by rindex
                    sent_array.append(sent[0:charlimit])
                    sent = sent[charlimit:]
            sent_array.append(sent)
        # print(len(sent_array), [len(x) for x in sent_array])
        return sent_array


# for Marian, by Dominik:
class MarianModel(Model):

    def __init__(self, cfg):
        super().__init__(cfg)
        self.spm_vocab = cfg['spm_vocab']
        self.spm_processor = spm.SentencePieceProcessor()
        self.spm_processor.Load(self.spm_vocab)
        if 'spm_limit' in cfg:
            self.spm_limit = cfg['spm_limit']
        else:
            self.spm_limit = 100

    def send_sentences_to_backend(self, sentences, src=None, tgt=None):
        marian_endpoint = "ws://{}/translate".format(self.server)
        log.debug("Connecting to '{}'".format(marian_endpoint))
        ws = create_connection(marian_endpoint)

        results = []

        batch = ""
        count = 0
        for sent in sentences:
            count += 1
            batch += sent + "\n"
            # TODO maybe batch size should be a model param.
            if count == current_app.config['MARIAN_BATCH_SIZE']:
                ws.send(batch)
                results.extend(ws.recv().strip().splitlines())
                count = 0
                batch = ""
        if count:
            ws.send(batch)
            results.extend(ws.recv().strip().splitlines())
        # print(result.rstrip())

        # close connection
        ws.close()
        return results

    def split_to_sent_array(self, text, lang):
        spm_limit = self.spm_limit
        spm_processor = self.spm_processor
        _ = "▁"  # words in sentencepieces start with this weird unicode underscore

        def decode(x):
            """convert sequence of sentencepieces back to the original string"""
            return "".join(x).replace(_, " ")

        def limit_sp(n, s):
            """n: take first n sentencepieces. Don't split it inside of a word, rather take less sentencepieces.
            s: sequence of sentencepieces
            """
            n -= 1
            while 0 < n < len(s) - 1 and not s[n + 1].startswith(_):
                n -= 1
            return s[:n + 1]

        sent_array = []
        for sent in split_text_into_sentences(text=text, language=lang):
            sp_sent = spm_processor.EncodeAsPieces(sent)
            # splitting to chunks of 100 (default) subwords, at most
            while len(sp_sent) > spm_limit:
                part = limit_sp(spm_limit, sp_sent)
                sent_array.append(decode(part))
                sp_sent = sp_sent[len(part):]
            sent_array.append(decode(sp_sent))
        # print(len(sent_array), [len(x) for x in sent_array], [len(spm_processor.EncodeAsPieces(x)) for x in sent_array])
        return sent_array
