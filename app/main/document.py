import os
import subprocess
import re
from typing import List, Tuple
from unicodedata import normalize
import logging

from flask import send_from_directory

from app.settings import ALLOWED_EXTENSIONS, UPLOAD_FOLDER, MAX_TEXT_LENGTH
from werkzeug.utils import secure_filename
from app.main.api.restplus import api

from app.text_utils import count_words, extract_text
from app.main.translate import translate_from_to, translate_with_model
from app.main.align import align_tokens

from app.main.translatable import Translatable
from document_translation.markuptranslator import MarkupTranslator, Translator
from document_translation.lindat_services.align import LindatAligner
from document_translation.regextokenizer import RegexTokenizer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict if "document_translation" in name]
for _logger in loggers:
    _logger.setLevel(logger.level)

class InnerLindatTranslator(Translator):
    def __init__(self, method, src, tgt, model=None):
        self.method = method
        self.src = src
        self.tgt = tgt
        self.model = model

    def translate(self, input_text: str) -> Tuple[List[str], List[str]]:
        logger.info("translator input text:")
        logger.info(repr(input_text))
        if self.method == "with_model":
            src_sents, tgt_sents = translate_with_model(self.model, input_text, self.src, self.tgt, return_source_sentences=True)
        else:
            src_sents, tgt_sents = translate_from_to(self.src, self.tgt, input_text, return_source_sentences=True)
        logger.info(f"Translated {len(src_sents)} sentences")

        # remove final newline (translator adds it)
        src_sents[-1] = src_sents[-1][:-1]
        tgt_sents[-1] = tgt_sents[-1][:-1]

        logger.info(src_sents)
        logger.info(tgt_sents)

        return src_sents, tgt_sents

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
        extension_check = '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
        return extension_check

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
        tikal_output = f"{self.orig_full_path}.{src}"
        assert os.path.exists(tikal_output)

        # read the extracted text from the uploaded file
        self.text = open(tikal_output).read()

        # count words and check length (without tags)
        text_without_tags = re.sub(r'<[^>]*>', '', self.text)
        self._input_word_count = count_words(text_without_tags)
        self._input_nfc_len = len(normalize('NFC', self.text))
        if self._input_nfc_len >= MAX_TEXT_LENGTH:
            api.abort(code=413, message='The total text length in the document exceeds the translation limit.')

        # initialize translation pipeline
        translator = InnerLindatTranslator(method, src, tgt, model)
        aligner = LindatAligner(src, tgt)
        tokenizer = RegexTokenizer()
        mt = MarkupTranslator(translator, aligner, tokenizer)

        # translate the text (possibly with markup)
        self.translation = mt.translate(self.text)

        # count words in translation
        self._output_word_count = len(self.translation.split())

        # write translation to file
        translated_text_path = f"{self.orig_full_path}.{tgt}"
        with open(translated_text_path, 'w') as f:
            f.write(self.translation)

        # reinsert translation using Tikal
        self.translated_path = f"{orig_root}.{tgt}{file_extension}"
        out = subprocess.run([TIKAL_PATH+'tikal.sh', '-lm', self.orig_full_path, '-sl', src, '-tl', tgt, '-overtrg', '-from', translated_text_path, '-to', self.translated_path])

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
