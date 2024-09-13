import os
import subprocess
import re
from typing import List, Tuple
from unicodedata import normalize

from flask import send_from_directory

from app.settings import ALLOWED_EXTENSIONS, UPLOAD_FOLDER, MAX_TEXT_LENGTH
from werkzeug.utils import secure_filename
from app.main.api.restplus import api

from app.text_utils import count_words
from app.main.translate import translate_from_to, translate_with_model

from app.main.translatable import Translatable
from document_translation.markuptranslator import MarkupTranslator, Translator
from document_translation.lindat_services.align import LindatAligner
from document_translation.regextokenizer import RegexTokenizer
from document_translation.pdf_tools.pdfeditor import PdfEditor

class InnerLindatTranslator(Translator):
    def __init__(self, method, src, tgt, model=None):
        self.method = method
        self.src = src
        self.tgt = tgt
        self.model = model

    def translate(self, input_text: str) -> Tuple[List[str], List[str]]:
        # translator does not like leading newlines, so we remove them and add them back later
        num_prefix_newlines = 0
        if input_text.startswith("\n"):
            while input_text[num_prefix_newlines] == "\n":
                num_prefix_newlines += 1
            input_text = input_text[num_prefix_newlines:]

        # remove final newline, translator adds it back so we don't want it to be there twice
        assert input_text.endswith("\n")
        input_text_stripped = input_text[:-1]

        # here we translate the text
        if self.method == "with_model":
            src_sentences, tgt_sentences = translate_with_model(self.model, input_text_stripped, self.src, self.tgt, return_source_sentences=True)
        else:
            src_sentences, tgt_sentences = translate_from_to(self.src, self.tgt, input_text_stripped, return_source_sentences=True)

        # post process the translation
        if tgt_sentences:
            # if the line was empty or whitespace-only, then discard any potential translation
            new_tgt_sentences: List[str] = []
            for src, tgt in zip(src_sentences, tgt_sentences):
                if re.match(r"^\s+$", src):
                    new_tgt_sentences.append(src)
                else:
                    new_tgt_sentences.append(tgt)
            tgt_sentences = new_tgt_sentences
            # reinsert prefix newlines
            src_sentences[0] = "\n" * num_prefix_newlines + src_sentences[0]
            tgt_sentences[0] = "\n" * num_prefix_newlines + tgt_sentences[0]
            # add spaces after sentence ends
            src_sentences = [src_sentence + " " if not src_sentence.endswith("\n") else src_sentence for src_sentence in src_sentences]
            tgt_sentences = [tgt_sentence + " " if not tgt_sentence.endswith("\n") else tgt_sentence for tgt_sentence in tgt_sentences]

        # remove final newline if there was none
        if not input_text.endswith("\n"):
            src_sentences[-1] = src_sentences[-1][:-1]
            tgt_sentences[-1] = tgt_sentences[-1][:-1]

        return src_sentences, tgt_sentences

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
        self._extract_translate_merge(src, tgt, "from_to")

    def translate_with_model(self, model, src, tgt):
        self._extract_translate_merge(src, tgt, "with_model", model)
    
    def _extract_translate_merge(self, src, tgt, method, model=None):
        if self.orig_full_path.endswith('.pdf'):
            self._extract_translate_merge_pdf(src, tgt, method, model=None)
        else:
            self._extract_translate_merge_document(src, tgt, method, model=None)
    
    def get_translated_path(self, tgt):
        orig_root, file_extension = os.path.splitext(self.orig_full_path)
        return f"{orig_root}.{tgt}{file_extension}"

    def _extract_translate_merge_document(self, src, tgt, method, model=None):
        TIKAL_PATH = "/home/balhar/okapi/"
        
        # run Tikal to extract text for translation
        out = subprocess.run([TIKAL_PATH+'tikal.sh', '-xm', self.orig_full_path, '-sl', src, '-to', self.orig_full_path])
        assert out.returncode == 0
        tikal_output = f"{self.orig_full_path}.{src}"
        assert os.path.exists(tikal_output)

        # read the extracted text from the uploaded file
        self.text = open(tikal_output).read()

        # translate the text
        self._translate(src, tgt, method, model)
    
        # write translation to file
        translated_text_path = f"{self.orig_full_path}.{tgt}"
        with open(translated_text_path, 'w') as f:
            f.write(self.translation)

        # reinsert translation using Tikal
        self.translated_path = self.get_translated_path(tgt)
        out = subprocess.run([TIKAL_PATH+'tikal.sh', '-lm', self.orig_full_path, '-sl', src, '-tl', tgt, '-overtrg', '-from', translated_text_path, '-to', self.translated_path])

    def _extract_translate_merge_pdf(self, src, tgt, method, model=None):
        # open the PDF file
        self.pdf_editor = PdfEditor(self.orig_full_path)

        # extract the text from the PDF
        lines = self.pdf_editor.extract_text()

        # join the extracted lines into a single string, separated by line breaks
        input_text = "<lb />".join(lines)
        assert "\n" not in input_text
        input_text = input_text.replace("<page-break />", "\n")
        self.text = input_text
        
        # translate the text
        self._translate(src, tgt, method, model)

        # split the translation into lines
        translated_lines = self.translation.replace("\n", "<page-break />").split("<lb />")
        assert len(lines) == len(translated_lines), f"{len(lines)} != {len(translated_lines)}"

        # merge the translated text into the PDF
        self.translated_path = self.get_translated_path(tgt)
        self.pdf_editor.merge_text(translated_lines, self.translated_path)

    def _translate(self, src, tgt, method, model=None):
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
