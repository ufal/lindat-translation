import json
import os
import tensorflow as tf
from tensor2tensor.utils import registry, usr_dir
from iso639 import to_name

from . import settings

usr_dir.import_usr_dir('t2t_usr_dir')
hparams = tf.contrib.training.HParams(data_dir=os.path.expanduser('t2t_data_dir'))

with open(os.path.join(os.path.dirname(__file__), 'models.json')) as models_json:
    models = json.load(models_json)

_model2problem = {}
_model2server = {}
_choices = []
_model_names = []
_default_model_name = models[0]['model']
for cfg in models:
    problem = registry.problem(cfg['problem'])
    problem.get_hparams(hparams)
    _model2problem[cfg['model']] = problem
    if cfg.get('default'):
        _default_model_name = cfg['model']
    _choices.append((cfg['model'], '{}->{}'.format(to_name(cfg['source']), to_name(cfg['target']))))
    _model_names.append(cfg['model'])
    if cfg.get('server'):
        _model2server[cfg['model']] = cfg['server']


def model2problem(model):
    if model in _model2problem:
        return _model2problem[model]
    else:
        return _model2problem[_default_model_name]


def get_choices():
    return _choices


def get_default_model_name():
    return _default_model_name


def get_model_names():
    return _model_names


def model2server(model):
    if model in _model2server:
        return _model2server[model]
    else:
        return settings.DEFAULT_SERVER
