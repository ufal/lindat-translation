import datetime
from flask import request
from flask.helpers import make_response
from flask_restx import Resource
from flask_restx.api import output_json

from app.main.api.restplus import api
from app.main.api.translation.parsers import text_input_with_src_tgt
from app.db import log_translation, log_access
from app.text_utils import extract_text
from app.main.translatable import Text, Document

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
                return Document.from_file(input_file)
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
            log_translation(src_lang=src, tgt_lang=tgt, src=translatable.get_text(), tgt=translatable.get_translation(),
                            author=author, frontend=frontend, ip_address=ip_address, input_type=input_type,
                            app_version=app_version, user_lang=user_lang)
