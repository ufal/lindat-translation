from math import ceil

import numpy as np
from flask import current_app, session
from sentence_splitter import split_text_into_sentences
from tensor2tensor.serving import serving_utils
from tensor2tensor.utils import registry

import app.models as models


class T2TModel(models.Model):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.problem = registry.problem(cfg['problem'])
        self.problem.get_hparams(models.hparams)

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