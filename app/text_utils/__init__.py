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
