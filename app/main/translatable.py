import os
import subprocess
import re
from unicodedata import normalize

from werkzeug.utils import secure_filename
from flask import send_from_directory
from flask_restx._http import HTTPStatus

from app.main.api.restplus import api
from app.text_utils import count_words, extract_text
from app.settings import ALLOWED_EXTENSIONS, UPLOAD_FOLDER, MAX_TEXT_LENGTH
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
        if self._input_nfc_len >= MAX_TEXT_LENGTH:
            api.abort(code=413, message='The data value transmitted exceeds the capacity limit.')
    
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

class Document(Translatable):
    def __init__(self, orig_full_path):
        self.orig_full_path = orig_full_path
        self._input_file_name = os.path.basename(orig_full_path)
        self._input_word_count = 0
        self._output_word_count = 0
        self._input_nfc_len = 0
    
    @classmethod
    def from_file(cls, request_file):
        if not request_file:
            api.abort(code=400, message='Empty file')
        
        if not cls.allowed_file(request_file.filename):
            api.abort(code=415, message='Unsupported file type for translation')

        filename = secure_filename(request_file.filename)

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        orig_full_path = os.path.join(UPLOAD_FOLDER, filename)
        request_file.save(orig_full_path)

        return cls(orig_full_path)

    @classmethod
    def allowed_file(cls, filename):
        return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def remove_tags(self, text):
        regex = r'</?(g|x|bx|ex|lb|mrk)(\s|\/?.*?)?>'
        text = re.sub(regex, ' ', text)
        text = re.sub(r'\s\s+', ' ', text)
        text = text.lstrip()
        text = text.rstrip()

        return text

    def translate_from_to(self, src, tgt):
        self._translate(src, tgt, "from_to")

    def translate_with_model(self, model, src, tgt):
        self._translate(src, tgt, "with_model", model)

    def _translate(self, src, tgt, method, model=None):
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
        # TODO: activate character limit for uploaded documents
        # print("line number",  len(lines))
        # if self._input_nfc_len >= MAX_TEXT_LENGTH:
        #     api.abort(code=413, message='The data value transmitted exceeds the capacity limit.')

        # translate
        if method == "with_model":
            self.translation = translate_with_model(model, removed_tags, src, tgt)
        else:
            self.translation = translate_from_to(src, tgt, removed_tags)
        self.translation = extract_text(self.translation)

        self._output_word_count = count_words(self.translation)

        # align
        source_tokens = [line.split() for line in removed_tags.split("\n")]
        target_tokens = [line.split() for line in self.translation.split("\n")]
        alignment = align_tokens(source_tokens, target_tokens, src, tgt)
        # write alignment
        alignment_path = self.orig_full_path+f".{src}-{tgt}.align.nomarkup"
        with open(alignment_path, 'w') as f:
            for al in alignment:
                alignment_string = [f"{a}-{b}" for a,b in al]
                alignment_string = " ".join(alignment_string)+"\n"
                f.write(alignment_string)
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
