import datetime
from unicodedata import normalize
from flask import request
from flask.helpers import make_response
from flask_restx import Resource
from flask_restx.api import output_json
from flask_restx._http import HTTPStatus

from app.main.api.restplus import api
from app.main.api.translation.parsers import text_input_with_src_tgt # , file_input
from app.db import log_translation, log_access
from app.text_utils import extract_text as _extract_text


class MyAbstractResource(Resource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_time = None
        self._input_file_name = None
        self._input_word_count = None
        self._input_nfc_len = None
        self.set_media_type_representations()

    @classmethod
    def to_text(cls, data, code, headers):
        return make_response(_extract_text(data), code, headers)

    def start_time_request(self):
        self._start_time = datetime.datetime.now()
        if request.files and 'input_text' in request.files:
            input_file = request.files.get('input_text')
            if input_file.content_type != 'text/plain':
                api.abort(code=415, message='Can only handle text/plain files.')
            text = input_file.read().decode('utf-8')
            self._input_file_name = input_file.filename or '_NO_FILENAME_SET'
        else:
            text = request.form.get('input_text')
            self._input_file_name = '_DIRECT_INPUT'
        if not text:
            api.abort(code=400, message='No text found in the input_text form/field or in request files')
        self._input_word_count = self._count_words(text)
        text = normalize('NFC', text)
        self._input_nfc_len = len(text)
        return text

    def get_additional_args_from_request(self):
        args = text_input_with_src_tgt.parse_args(request)
        return {
            'author': args.get('author') or 'unknown',
            'frontend': args.get('frontend') or args.get('X-Frontend') or 'unknown',
            'app_version': args.get('X-App-Version') or 'unknown',
            'user_lang': args.get('X-User-Language') or 'unknown',
            'input_type': args.get('inputType') or 'keyboard',
            'log_input': args.get('logInput', False),
            'ip_address': request.headers.get('X-Real-IP', 'unknown')
             }

    def set_media_type_representations(self):
        self.representations = self.representations if self.representations else {}
        if 'text/plain' not in self.representations:
            self.representations['text/plain'] = MyAbstractResource.to_text
        if 'application/json' not in self.representations:
            self.representations['application/json'] = output_json

    def create_response(self, translation, extra_msg):
        end = datetime.datetime.now()
        headers = {
            'X-Billing-Filename': self._input_file_name,
            'X-Billing-Input-Word-Count': self._input_word_count,
            'X-Billing-Output-Word-Count': self._count_words(translation),
            'X-Billing-Start-Time': self._start_time,
            'X-Billing-End-Time': end,
            'X-Billing-Duration': str(end - self._start_time),
            'X-Billing-Input-NFC-Len': self._input_nfc_len,
            'X-Billing-Extra': extra_msg
        }
        return translation, HTTPStatus.OK, headers

    def log_request(self, src, tgt, text, translation):
        self.log_request_with_additional_args(src=src, tgt=tgt, text=text, translation=translation, **self.get_additional_args_from_request())

    def log_request_with_additional_args(self, src, tgt, author, frontend, input_type, log_input, ip_address, text,
                                         translation, app_version, user_lang):
        duration_us = int((datetime.datetime.now() - self._start_time) / datetime.timedelta(microseconds=1))
        log_access(src_lang=src, tgt_lang=tgt, author=author, frontend=frontend,
                   input_nfc_len=self._input_nfc_len, duration_us=duration_us, input_type=input_type,
                   app_version=app_version, user_lang=user_lang)
        if log_input:
            log_translation(src_lang=src, tgt_lang=tgt, src=text, tgt=_extract_text(translation),
                            author=author, frontend=frontend, ip_address=ip_address, input_type=input_type,
                            app_version=app_version, user_lang=user_lang)

    @staticmethod
    def _count_words(translation):
        return len(_extract_text(translation).split())
