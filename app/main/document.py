import os
import subprocess
import sys
import re
import logging
from typing import List, Tuple
from unicodedata import normalize

from flask import send_from_directory
from flask import request

from app.settings import ALLOWED_EXTENSIONS, UPLOAD_FOLDER, MAX_TEXT_LENGTH, TIKAL_PATH
from werkzeug.utils import secure_filename
from app.main.api.restplus import api

from app.text_utils import count_words
from app.main.translate import translate_from_to, translate_with_model
from app.main.api.translation.parsers import text_input_with_src_tgt

from app.main.translatable import Translatable
from document_translation.markuptranslator import MarkupTranslator, Translator
from document_translation.lindat_services.align import LindatAligner
from document_translation.regextokenizer import RegexTokenizer
from document_translation.pdf_tools.pdfeditor import PdfEditor

import xml.etree.ElementTree as ET
from html import unescape

def normalize_xml_quotes_in_text(file_path):
    """
    Re-serialize XML so that double quotes in text content are literal "
    instead of &quot;. Tikal merge outputs &quot; in text; ElementTree
    keeps " in text and only escapes quotes in attributes.
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        with open(file_path, 'wb') as f:
            f.write(ET.tostring(root, encoding='utf-8', method='xml', default_namespace=None))
    except ET.ParseError:
        # If not valid XML or parse fails, leave file unchanged
        pass


def fix_html_entities_for_xml(content):
    """
    Convert HTML entities to XML-compatible numeric entities.
    This fixes issues where HTML entities like &nbsp; are not valid in XML.
    """
    # Common HTML entities that need to be converted to XML numeric entities
    html_entity_map = {
        '&nbsp;': '&#160;',   # Non-breaking space
        '&ensp;': '&#8194;',  # En space
        '&emsp;': '&#8195;',  # Em space
        '&thinsp;': '&#8201;', # Thin space
        '&zwnj;': '&#8204;',  # Zero width non-joiner
        '&zwj;': '&#8205;',   # Zero width joiner
        '&lrm;': '&#8206;',   # Left-to-right mark
        '&rlm;': '&#8207;',   # Right-to-left mark
        '&ndash;': '&#8211;', # En dash
        '&mdash;': '&#8212;', # Em dash
        '&lsquo;': '&#8216;', # Left single quotation mark
        '&rsquo;': '&#8217;', # Right single quotation mark
        '&sbquo;': '&#8218;', # Single low-9 quotation mark
        '&ldquo;': '&#8220;', # Left double quotation mark
        '&rdquo;': '&#8221;', # Right double quotation mark
        '&bdquo;': '&#8222;', # Double low-9 quotation mark
        '&dagger;': '&#8224;', # Dagger
        '&Dagger;': '&#8225;', # Double dagger
        '&permil;': '&#8240;', # Per mille sign
        '&lsaquo;': '&#8249;', # Single left-pointing angle quotation mark
        '&rsaquo;': '&#8250;', # Single right-pointing angle quotation mark
        '&euro;': '&#8364;',   # Euro sign
        '&trade;': '&#8482;',  # Trade mark sign
    }
    
    # Replace HTML entities with XML numeric entities
    for html_entity, xml_entity in html_entity_map.items():
        content = content.replace(html_entity, xml_entity)
    
    return content

class InnerLindatTranslator(Translator):
    def __init__(self, method, src, tgt, model=None, custom_prompt=None, terms=None, split=True):
        self.method = method
        self.src = src
        self.tgt = tgt
        self.model = model
        self.split = split
        self.custom_prompt = custom_prompt
    def translate(self, input_text: str, split=True) -> Tuple[List[str], List[str]]:
        # translator does not like leading newlines, so we remove them and add them back later
        num_prefix_newlines = 0
        if input_text.startswith("\n"):
            while input_text[num_prefix_newlines] == "\n":
                num_prefix_newlines += 1
            input_text = input_text[num_prefix_newlines:]
        num_suffix_newlines = 0
        if input_text.endswith("\n"):
            while input_text[-1 - num_suffix_newlines] == "\n":
                num_suffix_newlines += 1
            input_text = input_text[:-num_suffix_newlines]

        # here we translate the text
        if self.method == "with_model":
            src_sentences, tgt_sentences = translate_with_model(self.model, input_text, self.src, self.tgt, return_source_sentences=True, custom_prompt=self.custom_prompt, split=split)
        else:
            src_sentences, tgt_sentences = translate_from_to(self.src, self.tgt, input_text, return_source_sentences=True, custom_prompt=self.custom_prompt, split=split)

        # Debug: Print what we got from translation (will show in stderr)
        print(f"[DEBUG InnerLindatTranslator] Translation returned: src_count={len(src_sentences) if src_sentences else 0}, tgt_count={len(tgt_sentences) if tgt_sentences else 0}", file=sys.stderr, flush=True)
        if src_sentences and tgt_sentences:
            print(f"[DEBUG InnerLindatTranslator] First src (first 150 chars): {src_sentences[0][:150] if len(src_sentences[0]) > 150 else src_sentences[0]}", file=sys.stderr, flush=True)
            print(f"[DEBUG InnerLindatTranslator] First tgt (first 150 chars): {tgt_sentences[0][:150] if len(tgt_sentences[0]) > 150 else tgt_sentences[0]}", file=sys.stderr, flush=True)
            if len(src_sentences) != len(tgt_sentences):
                print(f"[DEBUG InnerLindatTranslator] CRITICAL: Length mismatch before post-processing: src={len(src_sentences)}, tgt={len(tgt_sentences)}", file=sys.stderr, flush=True)
                print(f"[DEBUG InnerLindatTranslator] src lengths: {[len(s) for s in src_sentences[:10]]}", file=sys.stderr, flush=True)
                print(f"[DEBUG InnerLindatTranslator] tgt lengths: {[len(s) for s in tgt_sentences[:10]]}", file=sys.stderr, flush=True)

        # post process the translation
        if tgt_sentences:
            # Check for length mismatch that could cause alignment issues
            if len(src_sentences) != len(tgt_sentences):
                print(f"[DEBUG InnerLindatTranslator] Length mismatch: src={len(src_sentences)}, tgt={len(tgt_sentences)}", file=sys.stderr, flush=True)
                print(f"[DEBUG InnerLindatTranslator] src lengths: {[len(s) for s in src_sentences[:5]]}...", file=sys.stderr, flush=True)
                print(f"[DEBUG InnerLindatTranslator] tgt lengths: {[len(s) for s in tgt_sentences[:5]]}...", file=sys.stderr, flush=True)
            
            # if the line was empty or whitespace-only, then discard any potential translation
            new_tgt_sentences: List[str] = []
            for i, (src, tgt) in enumerate(zip(src_sentences, tgt_sentences)):
                if re.match(r"^\s+$", src):
                    new_tgt_sentences.append(src)
                else:
                    new_tgt_sentences.append(tgt)
            tgt_sentences = new_tgt_sentences
            print(f"[DEBUG InnerLindatTranslator] After post-processing: tgt_count={len(tgt_sentences)}", file=sys.stderr, flush=True)
            # reinsert prefix newlines
            src_sentences[0] = "\n" * num_prefix_newlines + src_sentences[0]
            tgt_sentences[0] = "\n" * num_prefix_newlines + tgt_sentences[0]
            # reinsert suffix newlines
            src_sentences[-1] = src_sentences[-1].rstrip("\n") + "\n" * num_suffix_newlines
            tgt_sentences[-1] = tgt_sentences[-1].rstrip("\n") + "\n" * num_suffix_newlines
            # add spaces after sentence ends
            src_sentences = [src_sentence + " " if not src_sentence.endswith("\n") else src_sentence for src_sentence in src_sentences]
            tgt_sentences = [tgt_sentence + " " if not tgt_sentence.endswith("\n") else tgt_sentence for tgt_sentence in tgt_sentences]

        # Debug: Print what we're returning (will show in stderr)
        print(f"[DEBUG InnerLindatTranslator] Returning: src_count={len(src_sentences) if src_sentences else 0}, tgt_count={len(tgt_sentences) if tgt_sentences else 0}", file=sys.stderr, flush=True)
        if src_sentences and tgt_sentences and len(src_sentences) > 0 and len(tgt_sentences) > 0:
            print(f"[DEBUG InnerLindatTranslator] Returning first src (first 150 chars): {src_sentences[0][:150] if len(src_sentences[0]) > 150 else src_sentences[0]}", file=sys.stderr, flush=True)
            print(f"[DEBUG InnerLindatTranslator] Returning first tgt (first 150 chars): {tgt_sentences[0][:150] if len(tgt_sentences[0]) > 150 else tgt_sentences[0]}", file=sys.stderr, flush=True)
            # Check if they're the same (which would cause the alignment error)
            if src_sentences[0] == tgt_sentences[0]:
                print(f"[DEBUG InnerLindatTranslator] WARNING: First src and tgt sentences are IDENTICAL!", file=sys.stderr, flush=True)

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

    def translate_from_to(self, src, tgt, custom_prompt=None, terms=None, split=True):
        self._extract_translate_merge(src, tgt, "from_to", None, custom_prompt=custom_prompt, terms=terms, split=split)

    def translate_with_model(self, model, src, tgt, custom_prompt=None, terms=None, split=True):
        self._extract_translate_merge(src, tgt, "with_model", model, custom_prompt=custom_prompt, terms=terms, split=split)
    
    def _extract_translate_merge(self, src, tgt, method, model, custom_prompt=None, terms=None, split=True):
        if self.orig_full_path.endswith('.pdf'):
            self._extract_translate_merge_pdf(src, tgt, method, model, custom_prompt=custom_prompt, terms=terms, split=split)
        else:
            args = text_input_with_src_tgt.parse_args(request)
            if args.get('fraus', False):
                self._extract_translate_merge_fraus(src, tgt, method, model, custom_prompt=custom_prompt, terms=terms, split=split)
            else:
                self._extract_translate_merge_document(src, tgt, method, model, custom_prompt=custom_prompt, terms=terms, split=split)
    
    def get_translated_path(self, tgt):
        orig_root, file_extension = os.path.splitext(self.orig_full_path)
        return f"{orig_root}.{tgt}{file_extension}"

    def _extract_translate_merge_fraus(self, src, tgt, method, model, custom_prompt=None, terms=None, split=True):
        def fix_fraus_encoding(input_file, output_file):
            with open(input_file, 'r', encoding='utf-8') as f_in, open(output_file, 'w', encoding='utf-8') as f_out:
                for line in f_in:
                    if line.startswith('<?xml version="1.0" encoding="utf-16"?>'):
                        line = line.replace("utf-16", "utf-8")
                    f_out.write(line)

        def transform_lines(input_file, output_file, fun):
            with open(input_file, 'r', encoding='utf-8') as f_in, open(output_file, 'w', encoding='utf-8') as f_out:
                for line in f_in:
                    line = fun(line)
                    f_out.write(line)

        # fix the wrong encoding in the FRAUS XML
        xml_path = self.orig_full_path+".fixed"
        fix_fraus_encoding(self.orig_full_path, xml_path)

        # path to the `app` directory based on the current file
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        profile_xml = os.path.join(app_dir, 'okapi_profiles', 'okf_xml@fraus.fprm')

        # run Tikal first time to extract text and encoded html tags from the FRAUS XML
        out = subprocess.run([TIKAL_PATH+'tikal.sh', '-xm', xml_path, '-fc', profile_xml, '-sl', src, '-to', xml_path], stdout=subprocess.DEVNULL)
        assert out.returncode == 0
        tikal_output = f"{xml_path}.{src}"
        assert os.path.exists(tikal_output)

        # unescape the extracted text to reveal the html tags
        transform_lines(tikal_output, tikal_output+".html", unescape)

        # wrap each line in <p> tags to make them separate paragraphs
        def _wrap_in_p_tags(line):
            line_stripped = line.rstrip('\n')
            return f"<p>{line_stripped}</p>\n"
        transform_lines(tikal_output+".html", tikal_output+".html.p", _wrap_in_p_tags)

        # run Tikal again to extract the text within the html tags
        profile_html = os.path.join(app_dir, 'okapi_profiles', 'okf_html@fraus.fprm')
        out = subprocess.run([TIKAL_PATH+'tikal.sh', '-xm', tikal_output+".html.p", '-fc', profile_html, '-sl', src, '-to', tikal_output+".html.p"], stdout=subprocess.DEVNULL)
        assert out.returncode == 0
        tikal_output_2nd = tikal_output+f".html.p.{src}"
        assert os.path.exists(tikal_output_2nd)

        # read the extracted text
        self.text = open(tikal_output_2nd).read()

        # translate the text
        self._translate(src, tgt, method, model, custom_prompt=custom_prompt, terms=terms, split=split)
    
        # write translation to file
        translated_text_path = tikal_output + f".html.p.{tgt}"
        with open(translated_text_path, 'w') as f:
            f.write(self.translation)
        
        # reinsert translation into our paragraph tags
        translated_html = tikal_output + f".html.p.translated"
        out = subprocess.run([TIKAL_PATH+'tikal.sh', '-lm', tikal_output + f".html.p", '-fc', profile_html, '-sl', src, '-tl', tgt, '-overtrg', '-from', translated_text_path, '-to', translated_html], stdout=subprocess.DEVNULL)
        assert out.returncode == 0
        assert os.path.exists(translated_html)

        # unwrap the translated text from the <p> tags
        def _unwrap_p_tags(line):
            stripped_line = line.rstrip('\n')
            return stripped_line[3:-4] + "\n"
        transform_lines(translated_html, xml_path + ".translated", _unwrap_p_tags)
        
        # reinsert translation into FRAUS XML using Tikal
        self.translated_path = self.get_translated_path(tgt)
        out = subprocess.run([TIKAL_PATH+'tikal.sh', '-lm', xml_path, '-fc', profile_xml, '-sl', src, '-tl', tgt, '-overtrg', '-from', xml_path + ".translated", '-to', self.translated_path], stdout=subprocess.DEVNULL)
        assert out.returncode == 0
        assert os.path.exists(self.translated_path)
        # clean up the temporary files
        os.remove(self.orig_full_path)
        os.remove(xml_path)
        os.remove(tikal_output)
        os.remove(tikal_output_2nd)
        os.remove(translated_text_path)
        os.remove(translated_html)

    def _extract_translate_merge_document(self, src, tgt, method, model, custom_prompt=None, terms=None, split=True):
        # Fix HTML entities in XML files before processing
        if self.orig_full_path.endswith((".inxml", ".innopxml")):
            with open(self.orig_full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            content = fix_html_entities_for_xml(content)
            with open(self.orig_full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # run Tikal to extract text for translation
        tikal_command=[TIKAL_PATH+'tikal.sh', '-xm', self.orig_full_path, '-sl', src, '-to', self.orig_full_path]
        if self.orig_full_path.endswith(".inxml"):
            tikal_command.extend(["-fc",TIKAL_PATH+"okf_xml@all_inline"])
        elif self.orig_full_path.endswith(".innopxml"):
            tikal_command.extend(["-fc",TIKAL_PATH+"okf_xml@all_inline_not_paragraphs"])
        out = subprocess.run(tikal_command, stdout=sys.stderr, stderr=sys.stderr)
        assert out.returncode == 0
        tikal_output = f"{self.orig_full_path}.{src}"
        assert os.path.exists(tikal_output)

        # read the extracted text from the uploaded file
        self.text = open(tikal_output).read()

        # translate the text
        self._translate(src, tgt, method, model, custom_prompt=custom_prompt, terms=terms, split=split)
        translated_text_path = f"{self.orig_full_path}.{tgt}"

        with open(translated_text_path, 'w') as f:
            f.write(self.translation)#.replace(" NEWLINE ", "\n"))
        print("final translation", self.translation)
        # reinsert translation using Tikal
        self.translated_path = self.get_translated_path(tgt)
        tikal_command=[TIKAL_PATH+'tikal.sh', '-lm', self.orig_full_path, '-sl', src, '-tl', tgt, '-overtrg', '-from', translated_text_path, '-to', self.translated_path]
        if self.orig_full_path.endswith(".inxml"):
            tikal_command.extend(["-fc",TIKAL_PATH+"okf_xml@all_inline"])
        elif self.orig_full_path.endswith(".innopxml"):
            tikal_command.extend(["-fc",TIKAL_PATH+"okf_xml@all_inline_not_paragraphs"])
        out = subprocess.run(tikal_command, stdout=sys.stderr)
        assert out.returncode == 0
        assert os.path.exists(self.translated_path)
        # Tikal serializes quotes in text as &quot;; re-serialize so text has literal "
        if self.orig_full_path.endswith((".inxml", ".innopxml")):
            normalize_xml_quotes_in_text(self.translated_path)
        # clean up the temporary files
        os.remove(self.orig_full_path)
        os.remove(tikal_output)
        os.remove(translated_text_path)

    def _extract_translate_merge_pdf(self, src, tgt, method, model=None, custom_prompt=None, terms=None, split=True):
        # open the PDF file
        self.pdf_editor = PdfEditor(self.orig_full_path)

        # extract the text from the PDF
        lines = self.pdf_editor.extract_text()
        print("lines", lines)
        print("len(lines)", len(lines))
        # join the extracted lines into a single string, separated by line breaks
        input_text = "<lb />".join(lines)
        assert "\n" not in input_text
        input_text = input_text.replace("<page-break />", "\n")
        self.text = input_text
        
        # translate the text
        self._translate(src, tgt, method, model, custom_prompt=custom_prompt, terms=terms, split=split)

        # split the translation into lines
        translated_lines = self.translation.replace("\n", "<page-break />").split("<lb />")
        assert len(lines) == len(translated_lines), f"{len(lines)} != {len(translated_lines)}"

        # merge the translated text into the PDF
        self.translated_path = self.get_translated_path(tgt)
        print("translated_lines", translated_lines)
        print("len(translated_lines)", len(translated_lines))
        self.pdf_editor.merge_text(translated_lines, self.translated_path)

    def _translate(self, src, tgt, method, model=None, custom_prompt=None, terms=None, split=True):
        # count words and check length (without tags)by
        text_without_tags = re.sub(r'<[^>]*>', '', self.text)
        self._input_word_count = count_words(text_without_tags)
        self._input_nfc_len = len(normalize('NFC', self.text))

        # check if we want to ignore the size limit
        args = text_input_with_src_tgt.parse_args(request)
        ignore_size_limit = args.get('ignoreSizeLimit',False)

        # check the document character count limit
        if self._input_nfc_len >= MAX_TEXT_LENGTH and not ignore_size_limit:
            api.abort(code=413, message='The total text length in the document exceeds the translation limit.')

        # Check for problematic pattern: numbers with commas inside inline tags
        # This pattern can cause alignment issues because commas may be treated as sentence boundaries
        problematic_pattern = re.search(r'<[^>]+>[\d\s]*\d+,\d+[\d\s]*</[^>]+>', self.text)
        if problematic_pattern:
            print(f"[DEBUG] Found potentially problematic pattern (number with comma in tag): {problematic_pattern.group()}", file=sys.stderr, flush=True)
            print(f"[DEBUG] This may cause alignment issues if the comma is treated as a sentence boundary", file=sys.stderr, flush=True)

        # initialize translation pipeline
        translator = InnerLindatTranslator(method, src, tgt, model, custom_prompt=custom_prompt, terms=terms, split=split)
        aligner = LindatAligner(src, tgt, show_progress=False)
        tokenizer = RegexTokenizer()
        mt = MarkupTranslator(translator, aligner, tokenizer)

        
        self.translation = mt.translate(self.text)#.replace("\n", "<lb />"))

        # Unescape HTML/XML entities if requested (default: True)
        unescape_entities = args.get('unescapeEntities', True)
        if unescape_entities:
            self.translation = unescape(self.translation)

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
        # Do not remove the translated file - keep it for later use
        # os.remove(self.translated_path)
        return response
