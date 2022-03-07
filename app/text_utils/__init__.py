from collections import defaultdict
import os
from sentence_splitter import SentenceSplitter

pwd = os.path.dirname(os.path.abspath(__file__))
prefix_dir = os.path.join(pwd, 'non_breaking_prefixes')

_lang2file = defaultdict(lambda: None)
_lang2file['uk'] = os.path.join(prefix_dir, 'uk.txt')

_instances = {}


def split_text_into_sentences(text, language):
    instance = _instances.setdefault(language, SentenceSplitter(language, _lang2file[language]))
    return instance.split(text=text)
