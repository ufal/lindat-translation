import os
import logging
from flask import current_app
from iso639 import to_name

from app.dict_utils import get_or_create
import app.models as models

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Try to import tensor2tensor - make it optional
# Also check if T2T models are enabled in settings
T2T_AVAILABLE = False
hparams = None
def _check_t2t_availability():
    """Check if tensor2tensor is available and enabled"""
    global T2T_AVAILABLE, hparams
    
    # Check if T2T is enabled in settings
    try:
        from app import settings
        enable_t2t = getattr(settings, 'ENABLE_T2T_MODELS', True)
    except (ImportError, AttributeError):
        # Settings might not be loaded yet, default to True
        enable_t2t = True
    
    if not enable_t2t:
        log.info("tensor2tensor support is disabled in settings")
        return False
    
    # Try to import tensor2tensor
    try:
        from tensor2tensor.utils import usr_dir, hparam
        usr_dir.import_usr_dir('t2t_usr_dir')
        hparams = hparam.HParams(data_dir=os.path.expanduser('t2t_data_dir'))
        T2T_AVAILABLE = True
        log.info("tensor2tensor is available and enabled")
        return True
    except ImportError:
        log.warning("tensor2tensor is not available - T2T models will not be supported")
        return False

# Initialize T2T availability
_check_t2t_availability()


class Model(object):

    @staticmethod
    def create(cfg):
        if 'model_framework' in cfg:
            if cfg['model_framework'] == 'marian':
                return models.MarianModel(cfg)
            elif cfg['model_framework'] == 'tensorflow_doclevel':
                if not T2T_AVAILABLE:
                    raise ImportError("tensor2tensor is not available or disabled but tensorflow_doclevel model was requested")
                return models.T2TDocModel(cfg)
            elif cfg['model_framework'] == 'tensorflow_with_scores':
                if not T2T_AVAILABLE:
                    raise ImportError("tensor2tensor is not available or disabled but tensorflow_with_scores model was requested")
                return models.T2TModelWithScores(cfg)
            elif cfg['model_framework'] == 'oai_llm':
                return models.OaiLLMModel(cfg)
        # Default to T2T model only if T2T is available
        if not T2T_AVAILABLE:
            raise ImportError("tensor2tensor is not available or disabled and no model_framework specified")
        return models.T2TModel(cfg)

    @staticmethod
    def lang_list_display(lang_list):
        return ', '.join(map(to_name, lang_list))

    def __init__(self, cfg):
        self.model = cfg['model']
        self.name = self.model
        self.target_to_source = cfg.get('target_to_source', False)
        self.ignore_tags = cfg.get('ignore_tags', False)
        self.supports = {}
        for src_lang in cfg['source']:
            for tgt_lang in cfg['target']:
                targets = get_or_create(self.supports, src_lang)
                targets.append(tgt_lang)
                if self.target_to_source:
                    targets = get_or_create(self.supports, tgt_lang)
                    targets.append(src_lang)

        if 'sent_chars_limit' in cfg:
            self._sent_chars_limit = cfg['sent_chars_limit']

        if 'server' in cfg:
            self._server = cfg['server']

        if 'batch_size' in cfg:
            self._batch_size = cfg['batch_size']

        self.domain = cfg.get('domain', None)
        self.default = cfg.get('default', False)
        self.prefix_with = cfg.get('prefix_with', None)

        src = Model.lang_list_display(cfg['source'])
        tgt = Model.lang_list_display(cfg['target'])
        arrow = '->'
        if cfg.get('target_to_source', False):
            arrow = '<' + arrow
        self.title = '{name} {domain}({display})' \
            .format(name=cfg['model'],
                    display=cfg.get('display',
                                    '{src}{arrow}{tgt}'.format(src=src, arrow=arrow, tgt=tgt)),
                    domain='- ' + self.domain + ' domain - ' if self.domain else '')

    @property
    def server(self):
        """
        This method needs a valid app context, current_app is not available at init time.
        :return: host:port
        """
        if hasattr(self, '_server'):
            return self._server.format(**current_app.config)
        else:
            return current_app.config['DEFAULT_SERVER']

    @property
    def sent_chars_limit(self):
        """
        This method needs a valid app context, current_app is not available at init time.
        """
        if hasattr(self, '_sent_chars_limit'):
            return self._sent_chars_limit
        else:
            return current_app.config['SENT_LEN_LIMIT']

    @property
    def batch_size(self):
        """
        This method needs a valid app context, current_app is not available at init time.
        """
        if hasattr(self, '_batch_size'):
            return self._batch_size
        else:
            return current_app.config['BATCH_SIZE']

    def add_href(self, url):
        self.href = url

    def __iter__(self):
        yield 'model', self.model
        yield 'name', self.name
        yield 'supports', self.supports
        yield 'title', self.title
        if self.default:
            yield 'default', self.default
        if self.domain:
            yield 'domain', self.domain
        if self.href:
            yield 'href', self.href

    def translate(self, text, src=None, tgt=None, custom_prompt=None, terms=None, split=True):
        src = src or list(self.supports.keys())[0]
        tgt = tgt or self.supports[src][0]

        blocks_of_text, formatting = self.extract_blocks_of_text(text, src, split=split)
        outputs = self.send_blocks_to_backend(blocks_of_text, src, tgt, custom_prompt=custom_prompt, terms=terms)
        return self.reconstruct_formatting(outputs, formatting)

    def extract_blocks_of_text(self, text, text_lang, split=True):
        """
        Default block of text is a sentence
        :param text:
        :param text_lang:
        :return:
        """
        log.debug("Model::extract_blocks_of_text")
        return self.extract_sentences(text, text_lang,split=split)
    def send_blocks_to_backend(self, blocks, src, tgt, custom_prompt=None, terms=None):
        """
        By default calls send_sentences_to_backend
        :param blocks:
        :param src:
        :param tgt:
        :return:
        """
        log.debug("Model::send_blocks_to_backend")
        return self.send_sentences_to_backend(blocks, src, tgt, custom_prompt=custom_prompt, terms=terms)

    def send_sentences_to_backend(self, sentences, src, tgt, custom_prompt=None, terms=None):
        raise NotImplementedError("Abstract method")

    def extract_sentences(self, text, text_lang, split=True):
        sentences = []
        newlines_after = []
        if split:
            for segment in text.split('\n'):
                if segment:
                    sentences += self.split_to_sent_array(segment, lang=text_lang,
                                                      )
                newlines_after.append(len(sentences) - 1)
            return sentences, newlines_after
        else:
            return [text], [0]

    def split_to_sent_array(self, segment, lang):
        raise NotImplementedError("Abstract method")

    def reconstruct_formatting(self, outputs, newlines_after):
        for i in newlines_after:
            if i >= 0:
                outputs[i] += '\n'
        return outputs


