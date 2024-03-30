import datetime
import os
from unicodedata import normalize
from flask import request
from flask.helpers import make_response
from flask_restx import Resource
from flask_restx.api import output_json
from flask_restx._http import HTTPStatus
from werkzeug.utils import secure_filename

from app.main.api.restplus import api
from app.main.api.translation.parsers import text_input_with_src_tgt # , file_input
from app.db import log_translation, log_access
from app.text_utils import count_words, extract_text
from app.settings import ALLOWED_EXTENSIONS, UPLOAD_FOLDER
from app.main.translate import translate_from_to, translate_with_model

class Translatable:
    def translate_from_to(self, src, tgt):
        raise NotImplementedError()
    def translate_with_model(self, model, src, tgt):
        raise NotImplementedError()
    def get_text(self):
        raise NotImplementedError()
    def get_translation(self):
        raise NotImplementedError()
    def create_response(self, extra_headers, extra_msg):
        raise NotImplementedError()

class Text(Translatable):
    def __init__(self, text):
        self.text = text
        self.translation = ''
        self._input_file_name = '_DIRECT_INPUT'

        self._input_word_count = count_words(text)
        text = normalize('NFC', text)
        self._input_nfc_len = len(text)
    
    @classmethod
    def from_file(cls, input_file):
        text = input_file.read().decode('utf-8')
        obj = cls(text)
        obj._input_file_name = input_file.filename or '_NO_FILENAME_SET'

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
        return self.translation
    
    def create_response(self, extra_headers):
        headers = {
            'X-Billing-Filename': self._input_file_name,
            'X-Billing-Input-Word-Count': self._input_word_count,
            'X-Billing-Output-Word-Count': self._output_word_count,
            'X-Billing-Input-NFC-Len': self._input_nfc_len,
            **extra_headers
        }
        return self.translation, HTTPStatus.OK, headers

class Document(Translatable):
    pass

class MyAbstractResource(Resource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_time = None
        self.representations = {
            'text/plain': MyAbstractResource.to_text,
            'application/json': output_json,
        }

    @classmethod
    def to_text(cls, data, code, headers):
        return make_response(extract_text(data), code, headers)

    def start_time_request(self):
        self._start_time = datetime.datetime.now()

    def get_translatable_from_request(self):
        # if the request contains uploaded files
        if request.files and 'input_text' in request.files:
            input_file = request.files.get('input_text')
            if input_file.filename == '':
                api.abort(code=400, message='Empty filename')
            if input_file.content_type == 'text/plain':
                return Text.from_file(input_file)
            else:
                return Document(input_file)
        # if contains direct text
        elif request.form and 'input_text' in request.form:
            return Text(request.form.get('input_text'))
        else:
            api.abort(code=400, message='No text found in the input_text form/field or in request files')

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

    def extra_headers(self, extra_msg):
        end = datetime.datetime.now()
        return {
            'X-Billing-Start-Time': self._start_time,
            'X-Billing-End-Time': end,
            'X-Billing-Duration': str(end - self._start_time),
            'X-Billing-Extra': extra_msg
        }

    def log_request(self, src, tgt, translatable):
        self.log_request_with_additional_args(src=src, tgt=tgt, translatable=translatable, **self.get_additional_args_from_request())

    def log_request_with_additional_args(self, src, tgt, author, frontend, input_type, log_input, ip_address, translatable, app_version, user_lang):
        duration_us = int((datetime.datetime.now() - self._start_time) / datetime.timedelta(microseconds=1))
        log_access(src_lang=src, tgt_lang=tgt, author=author, frontend=frontend,
                   input_nfc_len=translatable._input_nfc_len, duration_us=duration_us, input_type=input_type,
                   app_version=app_version, user_lang=user_lang)
        if log_input:
            log_translation(src_lang=src, tgt_lang=tgt, src=translatable.get_text(), tgt=extract_text(translatable.get_translation()),
                            author=author, frontend=frontend, ip_address=ip_address, input_type=input_type,
                            app_version=app_version, user_lang=user_lang)
