import datetime
import os
import subprocess
import re
from unicodedata import normalize
from flask import request
from flask.helpers import make_response
from flask_restx import Resource
from flask_restx.api import output_json
from flask_restx._http import HTTPStatus
from werkzeug.utils import secure_filename
from flask import send_from_directory

from app.main.api.restplus import api
from app.main.api.translation.parsers import text_input_with_src_tgt # , file_input
from app.db import log_translation, log_access
from app.text_utils import count_words, extract_text
from app.settings import ALLOWED_EXTENSIONS, UPLOAD_FOLDER
from app.main.translate import translate_from_to, translate_with_model
from app.main.align import align_tokens

class Translatable:
    def __init__(self):
        self._input_file_name = None
        self._input_word_count = None
        self._output_word_count = None
        self._input_nfc_len = None

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

    def prep_billing_headers(self):
        return {
            'X-Billing-Filename': self._input_file_name,
            'X-Billing-Input-Word-Count': self._input_word_count,
            'X-Billing-Output-Word-Count': self._output_word_count,
            'X-Billing-Input-NFC-Len': self._input_nfc_len,
        }

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
        return extract_text(self.translation)
    
    def create_response(self, extra_headers):
        headers = {
            **self.prep_billing_headers(),
            **extra_headers
        }
        return self.translation, HTTPStatus.OK, headers

class Document(Translatable):
    def __init__(self, input_file):
        self.file = input_file
        self._input_word_count = 0
        self._output_word_count = 0
        self._input_nfc_len = 0

        if not input_file:
            api.abort(code=400, message='Empty file')
        
        if not self.allowed_file(input_file.filename):
            api.abort(code=415, message='Unsupported file type for translation')

        filename = secure_filename(input_file.filename)
        self._input_file_name = filename

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        self.orig_full_path = os.path.join(UPLOAD_FOLDER, filename)
        input_file.save(self.orig_full_path)

    def allowed_file(self, filename):
        return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def translate_from_to(self, src, tgt):
        pass

    def remove_tags(self, text):
        regex = r'</?(g|x|bx|ex|lb|mrk)(\s|\/?.*?)?>'
        text = re.sub(regex, ' ', text)
        text = re.sub(r'\s\s+', ' ', text)
        text = text.lstrip()
        text = text.rstrip()

        return text
    
    def translate_with_model(self, model, src, tgt):
        TIKAL_PATH = "/home/balhar/okapi/"
        orig_root, file_extension = os.path.splitext(self.orig_full_path)
        # run Tikal to extract text for translation
        out = subprocess.run([TIKAL_PATH+'tikal.sh', '-xm', self.orig_full_path, '-sl', src, '-to', self.orig_full_path])
        assert out.returncode == 0
        extracted_texts_path = self.orig_full_path+"."+src
        assert os.path.exists(extracted_texts_path)

        # remove markup
        with open(extracted_texts_path, 'r') as f:
            lines = f.readlines()
            self.text = "\n".join(lines)
        removed_tags = map(lambda x: self.remove_tags(x), lines)
        removed_tags = "\n".join(removed_tags)

        self._input_word_count = count_words(removed_tags)
        self._input_nfc_len = len(normalize('NFC', self.text))

        # translate
        self.translation = translate_with_model(model, removed_tags, src, tgt)
        self.translation = extract_text(self.translation)
        if self.translation.endswith("\n"):
            self.translation = self.translation[:-1]

        self._output_word_count = count_words(self.translation)

        # align
        source_tokens = [line.split() for line in removed_tags.split("\n")]
        target_tokens = [line.split() for line in self.translation.split("\n")]

        alignment = align_tokens(source_tokens, target_tokens, src, tgt)
        alignment = alignment["alignment"]
        # write alignment
        alignment_path = self.orig_full_path+f".{src}-{tgt}.align.nomarkup"
        with open(alignment_path, 'w') as f:
            for al in alignment:
                alignment_string = [f"{a}-{b}" for a,b in al]
                f.write(" ".join(alignment_string)+"\n")
        # reinsert tags
        reinserted_path = self.orig_full_path+f".{tgt}.withmarkup"
        with open(reinserted_path, 'w') as f:
            p = subprocess.Popen(['perl', '/home/balhar/document-translation/m4loc/xliff/reinsert_wordalign.pm', extracted_texts_path, alignment_path], stdin=subprocess.PIPE, stdout=f)
            p.communicate(self.translation.encode('utf-8'), timeout=15)
        # reinsert translation using Tikal
        self.translated_path = f"{orig_root}.{tgt}{file_extension}"
        out = subprocess.run([TIKAL_PATH+'tikal.sh', '-lm', self.orig_full_path, '-sl', src, '-tl', tgt, '-overtrg', '-from', reinserted_path, '-to', self.translated_path])
        
    def get_text(self):
        return self.text

    def get_translation(self):
        return self.translation

    def create_response(self, extra_headers):
        headers = {
            **self.prep_billing_headers(),
            **extra_headers
        }
        basename = os.path.basename(self.translated_path)
        response = send_from_directory(UPLOAD_FOLDER, basename)
        response.headers.extend(headers)
        return response

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
            log_translation(src_lang=src, tgt_lang=tgt, src=translatable.get_text(), tgt=translatable.get_translation(),
                            author=author, frontend=frontend, ip_address=ip_address, input_type=input_type,
                            app_version=app_version, user_lang=user_lang)
