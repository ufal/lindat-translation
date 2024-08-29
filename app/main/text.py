from unicodedata import normalize
from app.main.api.restplus import api
from flask_restx._http import HTTPStatus

from app.text_utils import count_words, extract_text
from app.settings import MAX_TEXT_LENGTH
from app.main.translate import translate_from_to, translate_with_model

from translatable import Translatable

class Text(Translatable):
    def __init__(self, text):
        self.text = text
        self.translation = ''
        self._input_file_name = '_DIRECT_INPUT'

        self._input_word_count = count_words(text)
        text = normalize('NFC', text)
        self._input_nfc_len = len(text)
        if self._input_nfc_len >= MAX_TEXT_LENGTH:
            api.abort(code=413, message='The total text length in the document exceeds the translation limit.')
    
    @classmethod
    def from_file(cls, request_file):
        text = request_file.read().decode('utf-8')
        obj = cls(text)
        obj._input_file_name = request_file.filename or '_NO_FILENAME_SET'

        return obj

    def translate_from_to(self, src, tgt):
        self.translation = translate_from_to(src, tgt, self.text)
        self._output_word_count = count_words(self.translation)
    
    def translate_with_model(self, model, src, tgt):
        self.translation = translate_with_model(model, self.text, src, tgt)
        self._output_word_count = count_words(self.translation)

    def get_text(self):
        return self.text

    def get_translation(self):
        return extract_text(self.translation)
    
    def create_response(self, extra_headers):
        headers = {
            **self.prep_billing_headers(),
            **extra_headers
        }
        return self.translation, HTTPStatus.OK, headers
