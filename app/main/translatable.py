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

TAG = "tag"
WHITESPACE = "wspace"
WORD = "word"

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

    tag_pattern = r'<\/?(g|x|bx|ex|lb|mrk).*?>'
    segments_regex = re.compile(r'('+tag_pattern+r'|\s+|[^<\s]+|[^>\s]+)')

    def words_tags_whitespaces(self, line):
        substrings = self.segments_regex.findall(line)
        substrings = [groups[0] for groups in substrings if groups]
        assert "".join(substrings) == line
        
        return self.substrings_to_segments(substrings)

    def substrings_to_segments(self, substrings):
        types = []
        for segment in substrings:
            if re.match(self.tag_pattern, segment):
                types.append(TAG)
            elif re.match(r'\s+', segment):
                types.append(WHITESPACE)
            else:
                types.append(WORD)
        return list(zip(substrings, types))

    def whitespaces_to_tags(self, segments):
        padded = [("", WHITESPACE)] + segments + [("", WHITESPACE)]
        result = []
        for i in range(1, len(padded) - 1):
            current = padded[i]
            previous = padded[i - 1]
            next = padded[i + 1]
            # we skip single spaces between words
            if current[0] == " " and previous[1] == WORD and next[1] == WORD:
                continue
            elif current[1] == WHITESPACE:
                result.append((f"<x equiv-text=\"{current[0]}\"/>", TAG))
            else:
                result.append(current)
        return result

    def tags_to_whitespaces(self, segments):
        padded = [("", WHITESPACE)] + segments + [("", WHITESPACE)]
        result = []
        for i in range(1, len(padded) - 1):
            current = padded[i]
            previous = padded[i - 1]
            next = padded[i + 1]
            # we keep single spaces between words
            if current[0] == " " and previous[1] == WORD and next[1] == WORD:
                result.append(current)
            # we remove any other whitespaces
            elif current[1] == WHITESPACE:
                # the line should contain only single spaces since we escaped anything else
                assert current[0] == " "
                continue
            elif current[0].startswith("<x equiv-text=\""):
                result.append((current[0][15:-3], WHITESPACE))
            else:
                result.append(current)
        return result

    def join_sentences_and_alignments(self, source_tokens, target_tokens, alignments):
        source_paragraphs = []
        target_paragraphs = []
        alignment_paragraphs = []
        print(source_tokens)

        src_current = []
        tgt_current = []
        align_current = []
        src_len = 0
        tgt_len = 0
        for source_sentence, target_sentence, alignment in zip(source_tokens, target_tokens, alignments):
            print(source_sentence, target_sentence, alignment)
            src_current += source_sentence
            tgt_current += target_sentence
            offset_alignment = [(s + src_len, t + tgt_len) for s, t in alignment]
            align_current += offset_alignment
            src_len += len(source_sentence)
            tgt_len += len(target_sentence)
            last_token = source_sentence[-1]
            if last_token.endswith("\n"):
                assert target_sentence[-1].endswith("\n")
                source_paragraphs.append(src_current)
                target_paragraphs.append(tgt_current)
                alignment_paragraphs.append(align_current)
                src_current = []
                tgt_current = []
                align_current = []
                src_len = 0
                tgt_len = 0
                for i in range(len(last_token) - 2, 0, -1):
                    if last_token[i] == "\n":
                        source_paragraphs.append([])
                        target_paragraphs.append([])
                        alignment_paragraphs.append([])
        if len(src_current) > 0:
            source_paragraphs.append(src_current)
            target_paragraphs.append(tgt_current)
            alignment_paragraphs.append(align_current)
        return source_paragraphs, target_paragraphs, alignment_paragraphs

    def remove_tags(self, segments):
        return [s for s in segments if s[1] != TAG]

    def segments_to_text(self, segments, sep=" "):
        return sep.join(s[0] for s in segments)

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
        with open(extracted_texts_path) as f:
            lines = f.read().splitlines()
            self.text = "\n".join(lines) + "\n"
        words_tags_whitespaces = [self.words_tags_whitespaces(x) for x in lines]
        words_tags = [self.whitespaces_to_tags(w) for w in words_tags_whitespaces]
        words = [self.remove_tags(w) for w in words_tags]
        words_str = [self.segments_to_text(w) for w in words]

        removed_tags = "\n".join(words_str) + "\n"

        # write text with encoded whitespaces
        words_tags_str = map(lambda x: self.segments_to_text(x), words_tags)
        words_tags_str = "\n".join(words_tags_str) + "\n"
        extracted_texts_encoded_whitespaces_path = self.orig_full_path+"."+src+".withmarkup.encoded"
        with open(extracted_texts_encoded_whitespaces_path, 'w') as f:
            f.write(words_tags_str)

        self._input_word_count = count_words(removed_tags)
        self._input_nfc_len = len(normalize('NFC', self.text))

        # TODO: activate character limit for uploaded documents
        # print("line number",  len(lines))
        # if self._input_nfc_len >= MAX_TEXT_LENGTH:
        #     api.abort(code=413, message='The data value transmitted exceeds the capacity limit.')

        # translate
        print("Translating")
        if method == "with_model":
            src_sents, tgt_sents = translate_with_model(model, removed_tags, src, tgt, return_source_sentences=True)
        else:
            src_sents, tgt_sents = translate_from_to(src, tgt, removed_tags, return_source_sentences=True)
        self.translation = extract_text(tgt_sents)

        self._output_word_count = count_words(self.translation)

        # align
        print("Aligning")
        source_tokens = [sentence.split(" ") for sentence in src_sents]
        target_tokens = [sentence.split(" ") for sentence in tgt_sents]
        alignment = align_tokens(source_tokens, target_tokens, src, tgt)
        _, _, alignment = self.join_sentences_and_alignments(source_tokens, target_tokens, alignment)
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
            p = subprocess.Popen(['perl', '/home/balhar/document-translation/m4loc/xliff/reinsert_wordalign.pm', extracted_texts_encoded_whitespaces_path, alignment_path], stdin=subprocess.PIPE, stdout=f)
            p.communicate(self.translation.encode('utf-8'), timeout=15)
        with open(reinserted_path, 'r') as f:
            reinserted = f.read().splitlines()
        
        reinserted_segments = [self.words_tags_whitespaces(line) for line in reinserted]
        decoded_whitespaces = [self.tags_to_whitespaces(line) for line in reinserted_segments]
        reconstructed = "\n".join([self.segments_to_text(line, sep="") for line in decoded_whitespaces]) + "\n"

        reconstructed_path = self.orig_full_path+f".{tgt}.withmarkup.decoded"
        with open(reconstructed_path, 'w') as f:
            f.write(reconstructed)
        
        # reinsert translation using Tikal
        self.translated_path = f"{orig_root}.{tgt}{file_extension}"
        out = subprocess.run([TIKAL_PATH+'tikal.sh', '-lm', self.orig_full_path, '-sl', src, '-tl', tgt, '-overtrg', '-from', reconstructed_path, '-to', self.translated_path])

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
