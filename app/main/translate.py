from math import ceil
import numpy as np
from tensor2tensor.serving import serving_utils
from sentence_splitter import split_text_into_sentences
from app.logging_utils import logged
from app.model_settings import models
# TODO get rid of these
from flask import current_app, session

# for Marian, by Dominik:
from websocket import create_connection
import sentencepiece as spm

import logging
log = logging.getLogger(__name__)


def translate_with_marian_model(model, sentences):
    marian_endpoint = "ws://{}/translate".format(model.server)
    log.debug("Connecting to '{}'".format(marian_endpoint))
    ws = create_connection(marian_endpoint)

    results = []

    batch = ""
    count = 0
    for sent in sentences:
        count += 1
        batch += sent + "\n"
        # TODO maybe batch size should be a model param.
        if count == 8: #current_app.config['MARIAN_BATCH_SIZE']:
            ws.send(batch)
            results.extend(ws.recv().strip().splitlines())
            count = 0
            batch = ""
    if count:
        ws.send(batch)
        results.extend(ws.recv().strip().splitlines())
    #print(result.rstrip())

    # close connection
    ws.close()
    return results


def translate_with_model(model, text, src=None, tgt=None):
    if not text or not text.strip():
        return []

    src = src or model.supports.keys()[0]
    tgt = tgt or model.supports[src][0]

    if model.prefix_with:
        prefix = model.prefix_with.format(source=src, target=tgt)
    else:
        prefix = ''

    src_lang = src
    sentences = []
    newlines_after = []
    for segment in text.split('\n'):
        if segment:
            sentences += split_to_sent_array(segment, lang=src_lang, charlimit=model.sent_chars_limit, spm_limit=model.spm_limit, spm_processor=model.spm_processor)
        newlines_after.append(len(sentences)-1)
    outputs = []

    if model.model_framework == 'marian':
        outputs = translate_with_marian_model(model, sentences)
    else:
        request_fn = serving_utils.make_grpc_request_fn(servable_name=model.model, timeout_secs=500,
                                                        server=model.server)

        for batch in np.array_split(sentences, ceil(len(sentences)/current_app.config['BATCH_SIZE'])):
            try:
                outputs += list(map(lambda sent_score: sent_score[0],
                                    serving_utils.predict([prefix + sent for sent in batch.tolist()],
                                                            model.problem,
                                                          request_fn)))
            except:
                # When tensorflow serving restarts web clients seem to "remember" the channel where
                # the connection have failed. clearing up the session, seems to solve that
                session.clear()
                raise
    for i in newlines_after:
        if i >= 0:
            outputs[i] += '\n'
    return outputs


def translate_from_to(source, target, text):
    models_on_path = models.get_model_list(source, target)
    if not models_on_path:
        raise ValueError('No models found for the given pair')
    translation = []
    for obj in models_on_path:
        translation = translate_with_model(obj['model'], text, obj['src'], obj['tgt'])
        text = ' '.join(translation).replace('\n ', '\n')
    return translation


def split_to_sent_array_by_char_limit(text, lang, charlimit):
    sent_array = []
    for sent in split_text_into_sentences(text=text, language=lang):
        while len(sent) > limit:
            try:
                # When sent starts with a space, then sent[0:0] was an empty string, 
                # and it caused an infinite loop. This fixes it. 
                beg = 0
                while sent[beg] == ' ':
                    beg += 1
                last_space_idx = sent.rindex(" ", beg, limit)
                sent_array.append(sent[0:last_space_idx])
                sent = sent[last_space_idx:]
            except ValueError:
                # raised if no space found by rindex
                sent_array.append(sent[0:limit])
                sent = sent[limit:]
        sent_array.append(sent)
    print(len(sent_array), [len(x) for x in sent_array])
    return sent_array

@logged()
def split_to_sent_array(text, lang, charlimit=None, spm_limit=None, spm_processor=None):
    if spm_processor is None:
        return split_to_sent_array_by_char_limit(text, lang, charlimit)

    _ = "▁"

    def decode(x):
        return "".join(x).replace(_," ")

    def limit_sp(n, s):
        n -= 1
        while 0<n<len(s)-1 and not s[n+1].startswith(_):
            n -= 1
        return s[:n+1]

    sent_array = []
    for sent in split_text_into_sentences(text=text, language=lang):
        sp_sent = spm_processor.EncodeAsPieces(sent)
        while len(sp_sent) > spm_limit:
            part = limit_sp(spm_limit, sp_sent)
            sent_array.append(decode(part))
            sp_sent = sp_sent[len(part):]
        sent_array.append(decode(sp_sent))
    print(len(sent_array), [len(x) for x in sent_array], [len(spm_processor.EncodeAsPieces(x)) for x in sent_array])
    return sent_array
