from collections import defaultdict
import os
from sentence_splitter import SentenceSplitter

pwd = os.path.dirname(os.path.abspath(__file__))
prefix_dir = os.path.join(pwd, 'non_breaking_prefixes')

_lang2file = defaultdict(lambda: None)
_lang2file['uk'] = os.path.join(prefix_dir, 'uk.txt')

_instances = {}


def split_text_into_sentences(text, language):
    if language not in _instances:
        instance = SentenceSplitter(language, _lang2file[language])
        _instances[language] = instance
    else:
        instance = _instances[language]
    return instance.split(text=text)


def extract_text(translation):
    if translation:
        if isinstance(translation[0], str):
            text_arr = translation
        elif isinstance(translation[0], list):
            text_arr = [t[0] for t in translation]
        elif isinstance(translation[0], dict):
            text_arr = [t['output_text'] for t in translation]
        else:
            text_arr = []
    else:
        text_arr = []
    return ' '.join(text_arr).replace('\n ', '\n')

def count_words(translation):
    return len(extract_text(translation).split())

