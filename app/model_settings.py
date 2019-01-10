import json
import os
from flask import current_app
import tensorflow as tf
from tensor2tensor.utils import registry, usr_dir
from iso639 import to_name
import networkx as nx

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
_G = nx.DiGraph()
for cfg in models:
    problem = registry.problem(cfg['problem'])
    problem.get_hparams(hparams)
    _model2problem[cfg['model']] = problem
    if cfg.get('default'):
        _default_model_name = cfg['model']
    _choices.append((cfg['model'], '{} ({})'.format(cfg['model'],
                                                    cfg.get('display', '{}->{}'
                                                            .format(to_name(cfg['source']),
                                                                    to_name(cfg['target']))))))
    _model_names.append(cfg['model'])
    if cfg.get('server'):
        _model2server[cfg['model']] = cfg['server']
    # This will keep only the last model
    _G.add_edge(cfg['source'], cfg['target'], cfg=cfg)

# There may be more than one shortest path between sa source and target; this returns only one
_shortest_path = nx.shortest_path(_G)
_directions = []
for item in _shortest_path.items():
    u = item[0]
    for v in item[1].keys():
        if u != v:
            display = '{}->{}'.format(to_name(u), to_name(v))
            _directions.append((u, v, display))
_directions = sorted(_directions, key=lambda x: x[2])


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
    """
    This method needs a valid app context
    :param model:
    :return:
    """
    if model in _model2server:
        return _model2server[model].format(**current_app.config)
    else:
        return current_app.config['DEFAULT_SERVER']


def get_model_list(source, target):
    """
    Returns a list of models that need to be used to translate from source to target
    :param source:
    :param target:
    :return:
    """
    try:
        path = _shortest_path[source][target]
        if len(path) > 1:
            return [_G[pair[0]][pair[1]]['cfg']['model'] for pair in zip(path[0:-1], path[1:])]
        else:
            return []
    except KeyError as e:
        return []


def get_possible_directions():
    return _directions
