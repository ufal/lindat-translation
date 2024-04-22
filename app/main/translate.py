#from app.logging_utils import logged
from app.model_settings import models
from app.text_utils import extract_text as _extract_text

import logging
log = logging.getLogger(__name__)


def translate_with_model(model, text, src=None, tgt=None, return_source_sentences=False):
    if not text or not text.strip():
        return []
    if return_source_sentences:
        src_sents = model.reconstruct_formatting(*model.extract_sentences(text, src))
        tgt_sents = model.translate(text, src, tgt)
        return src_sents, tgt_sents
    else:
        return model.translate(text, src, tgt)


def translate_from_to(source, target, text, return_source_sentences=False):
    models_on_path = models.get_model_list(source, target)
    if not models_on_path:
        raise ValueError('No models found for the given pair')

    if return_source_sentences:
        first_model = models_on_path[0]['model']
        src_sents = first_model.reconstruct_formatting(*first_model.extract_sentences(text, source))

    translation = []
    for obj in models_on_path:
        translation = translate_with_model(obj['model'], text, obj['src'], obj['tgt'])
        text = _extract_text(translation)
    
    if return_source_sentences:
        return src_sents, translation
    else:
        return translation
