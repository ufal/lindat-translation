import sentencepiece as spm
from flask import current_app
from sentence_splitter import split_text_into_sentences
from websocket import create_connection

import app.models as models


# for Marian, by Dominik:
class MarianModel(models.Model):

    def __init__(self, cfg):
        super().__init__(cfg)
        self.spm_vocab = cfg['spm_vocab']
        self.spm_processor = spm.SentencePieceProcessor()
        self.spm_processor.Load(self.spm_vocab)
        if 'spm_limit' in cfg:
            self.spm_limit = cfg['spm_limit']
        else:
            self.spm_limit = 100

    @property
    def batch_size(self):
        """
        This method needs a valid app context, current_app is not available at init time.
        """
        if hasattr(self, '_batch_size'):
            return self._batch_size
        else:
            return current_app.config['MARIAN_BATCH_SIZE']

    def send_sentences_to_backend(self, sentences, src=None, tgt=None):
        marian_endpoint = "ws://{}/translate".format(self.server)
        models.log.debug("Connecting to '{}'".format(marian_endpoint))
        ws = create_connection(marian_endpoint)

        results = []

        batch = ""
        count = 0
        for sent in sentences:
            count += 1
            batch += sent + "\n"
            if count == self.batch_size:
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