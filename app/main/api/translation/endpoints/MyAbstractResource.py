import datetime
from flask import request
from flask.helpers import make_response
from flask_restplus import Resource
from flask_restplus.api import output_json
from flask_restplus._http import HTTPStatus

from app.main.api.restplus import api


class MyAbstractResource(Resource):

    @classmethod
    def to_text(cls, data, code, headers):
        return make_response(' '.join(data).replace('\n ', '\n'), code, headers)

    def get_text_from_request(self):
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
        self._input_word_count = self._count_words(text)
        return text

    def set_media_type_representations(self):
        self.representations = self.representations if self.representations else {}
        if 'text/plain' not in self.representations:
            self.representations['text/plain'] = MyAbstractResource.to_text
        if 'application/json' not in self.representations:
            self.representations['application/json'] = output_json

    def create_response(self, translation):
        end = datetime.datetime.now()
        headers = {
            'X-Billing-Filename': self._input_file_name,
            'X-Billing-Input-Word-Count': self._input_word_count,
            'X-Billing-Output-Word-Count': self._count_words(' '.join(translation).replace('\n ',
                                                                                           '\n')),
            'X-Billing-Start-Time': self._start_time,
            'X-Billing-End-Time': end,
            'X-Billing-Duration': str(end - self._start_time)
        }
        return translation, HTTPStatus.OK, headers


    @staticmethod
    def _count_words(text):
        return len(text.split())
