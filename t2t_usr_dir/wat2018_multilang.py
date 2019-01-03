from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Dependency imports

from tensor2tensor.data_generators import generator_utils
from tensor2tensor.data_generators import problem
from tensor2tensor.data_generators import text_encoder
from tensor2tensor.data_generators import translate
from tensor2tensor.utils import registry
from tensor2tensor.models import transformer

import tensorflow as tf

FLAGS = tf.flags.FLAGS

# End-of-sentence marker.
EOS = text_encoder.EOS_ID

_datasets = {
    'ENHI_train': [["", ("ENHI.wat.en", "ENHI.wat.hi")]],
    'ENHI_dev': [["", ("ENHI.wat.dev.en", "ENHI.wat.dev.hi")]],
}


@registry.register_problem
class TranslateEnhiWat18(translate.TranslateProblem):
    @property 
    def approx_vocab_size(self):
        return 2 ** 15  # 32768 
    
    @property
    def vocab_filename(self):
        return "vocab.enhi.32768"
    def source_data_files(self, dataset_split):
        train = dataset_split == problem.DatasetSplit.TRAIN
        return _datasets['ENHI_train'] if train else _datasets['ENHI_dev']


