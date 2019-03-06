from math import ceil
import numpy as np
from tensor2tensor.serving import serving_utils
from sentence_splitter import split_text_into_sentences
from app.logging_utils import logged
from app.model_settings import model2problem, model2server, get_model_list
# TODO get rid of these
from flask import current_app, session


def translate_with_model(model, text):
    if not text or not text.strip():
        return []
    request_fn = serving_utils.make_grpc_request_fn(servable_name=model, timeout_secs=500,
                                                    server=model2server(model))
    lang = model.split('-')[0]
    sentences = []
    newlines_after = []
    for segment in text.split('\n'):
        if segment:
            sentences += split_to_sent_array(segment, lang=lang)
        newlines_after.append(len(sentences)-1)
    outputs = []
    for batch in np.array_split(sentences, ceil(len(sentences)/current_app.config['BATCH_SIZE'])):
        try:
            outputs += list(map(lambda sent_score: sent_score[0],
                                serving_utils.predict(batch.tolist(), model2problem(model), request_fn)))
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
    models_on_path = get_model_list(source, target)
    translation = []
    for cfg in models_on_path:
        translation = translate_with_model(cfg['model'], text)
        text = ' '.join(translation).replace('\n ', '\n')
    return translation


@logged()
def split_to_sent_array(text, lang):
    sent_array = []
    limit = current_app.config['SENT_LEN_LIMIT']
    for sent in split_text_into_sentences(text=text, language=lang):
        while len(sent) > limit:
            try:
                last_space_idx = sent.rindex(" ", 0, limit)
                sent_array.append(sent[0:last_space_idx])
                sent = sent[last_space_idx:]
            except ValueError:
                sent_array.append(sent[0:limit])
                sent = sent[limit:]
        sent_array.append(sent)
    return sent_array
