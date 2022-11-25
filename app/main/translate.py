#from app.logging_utils import logged
from app.model_settings import models
from app.text_utils import extract_text as _extract_text

import logging
log = logging.getLogger(__name__)


def translate_with_model(model, text, src=None, tgt=None):
    if not text or not text.strip():
        return []
    return model.translate(text, src, tgt)


def translate_from_to(source, target, text):
    models_on_path = models.get_model_list(source, target)
    if not models_on_path:
        raise ValueError('No models found for the given pair')
    translation = []
    for obj in models_on_path:
        translation = translate_with_model(obj['model'], text, obj['src'], obj['tgt'])
        text = _extract_text(translation)
    return translation
