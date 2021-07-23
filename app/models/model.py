import os
import logging
from flask import current_app
from iso639 import to_name
from tensor2tensor.utils import usr_dir, hparam

from app.dict_utils import get_or_create
import app.models as models

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
usr_dir.import_usr_dir('t2t_usr_dir')
hparams = hparam.HParams(data_dir=os.path.expanduser('t2t_data_dir'))


class Model(object):

    @staticmethod
    def create(cfg):
        if 'model_framework' in cfg:
            if cfg['model_framework'] == 'marian':
                return models.MarianModel(cfg)
            elif cfg['model_framework'] == 'tensorflow_doclevel':
                return models.T2TDocModel(cfg)
        return models.T2TModel(cfg)

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

        blocks_of_text, formatting = self.extract_blocks_of_text(text, src)
        outputs = self.send_blocks_to_backend(blocks_of_text, src, tgt)
        return self.reconstruct_formatting(outputs, formatting)

    def extract_blocks_of_text(self, text, text_lang):
        """
        Default block of text is a sentence
        :param text:
        :param text_lang:
        :return:
        """
        log.error("Model::extract_blocks_of_text")
        return self.extract_sentences(text, text_lang)

    def send_blocks_to_backend(self, blocks, src, tgt):
        """
        By default calls send_sentences_to_backend
        :param blocks:
        :param src:
        :param tgt:
        :return:
        """
        log.error("Model::send_blocks_to_backend")
        return self.send_sentences_to_backend(blocks, src, tgt)

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


