import json
import logging
import os
from flask import current_app
import tensorflow as tf
from tensor2tensor.utils import registry, usr_dir
from iso639 import to_name
import networkx as nx

from . import settings

log = logging.getLogger(__name__)

usr_dir.import_usr_dir('t2t_usr_dir')
hparams = tf.contrib.training.HParams(data_dir=os.path.expanduser('t2t_data_dir'))


#TODO handle prefix_with
#TODO src/tgt as array
class Models(object):

    def __init__(self, models_cfg):
        self._models = {}
        self._default_model_name = models_cfg[0]['model']
        self._G = nx.DiGraph()
        for cfg in models_cfg:
            if not isinstance(cfg['source'], list) or not isinstance(cfg['target'], list):
                log.error("Error in config source and target must be lists")
                import sys
                sys.exit(1)
            model = Model(cfg)
            if model.model in self._models:
                log.error("Model names should be unique")
                import sys
                sys.exit(1)
            self._models[model.model] = model
            if cfg.get('default'):
                _default_model_name = cfg['model']

            flip_src_tgt = cfg.get('target_to_source', False)
            for src_lang in cfg['source']:
                for tgt_lang in cfg['target']:
                    # This will keep only the last model
                    self._G.add_edge(src_lang, tgt_lang, cfg=model)
                    if flip_src_tgt:
                        self._G.add_edge(tgt_lang, src_lang, cfg=model)

        # There may be more than one shortest path between sa source and target; this returns only one
        self._shortest_path = nx.shortest_path(self._G)
        _directions = []
        for item in self._shortest_path.items():
            u = item[0]
            for v in item[1].keys():
                if u != v:
                    display = '{}->{}'.format(to_name(u), to_name(v))
                    _directions.append((u, v, display))
        self._directions = sorted(_directions, key=lambda x: x[2])

    def get_possible_directions(self):
        return self._directions

    def get_model_list(self, source, target):
        """
        Returns a list of models that need to be used to translate from source to target
        :param source:
        :param target:
        :return:
        """
        try:
            path = self._shortest_path[source][target]
            if len(path) > 1:
                # TODO cfg is now a model class
                return [self._G[pair[0]][pair[1]]['cfg'] for pair in zip(path[0:-1], path[1:])]
            else:
                return []
        except KeyError as e:
            return []

    def get_default_model_name(self):
        return self._default_model_name

    def get_model_names(self):
        return list(self._models.keys())

    def get_models(self):
        # TODO this used to return the json cfg not model classes
        return list(self._models.values())

    def get_model(self, model_name):
        return self._models.get(model_name, self._models.get(self.get_default_model_name()))


class Model(object):

    @staticmethod
    def lang_list_display(lang_list):
        return ', '.join(map(to_name, lang_list))

    @staticmethod
    def get_or_create_list(aDict, key):
        arr = aDict.get(key, [])
        aDict[key] = arr
        return arr

    def __init__(self, cfg):
        self.model = cfg['model']
        self.target_to_source = cfg.get('target_to_source', False)

        self.supports = {}
        for src_lang in cfg['source']:
            for tgt_lang in cfg['target']:
                targets = Model.get_or_create_list(self.supports, src_lang)
                targets.append(tgt_lang)
                if self.target_to_source:
                    targets = Model.get_or_create_list(self.supports, tgt_lang)
                    targets.append(src_lang)

        self.problem = registry.problem(cfg['problem'])
        self.problem.get_hparams(hparams)
        if 'server' in cfg:
            self._server = cfg['server']
        self.domain = cfg.get('domain', None)
        self.default = cfg.get('default', False)
        self.prefix_with = cfg.get('prefix_with', None)

        if self.domain:
            ' ({})'.format(self.domain)
        src = Model.lang_list_display(cfg['source'])
        tgt = Model.lang_list_display(cfg['target'])
        arrow = '->'
        if cfg.get('target_to_source', False):
            arrow = '<' + arrow
        self.title = '{} ({}{})'.format(cfg['model'], cfg.get('display', '{src}{arrow}{tgt}'
                                                              .format(src=src, arrow=arrow, tgt=tgt)),
                                        self.domain)

    @property
    def server(self):
        """
        This method needs a valid app context
        :return:
        """
        if hasattr(self, '_server'):
            return self._server.format(**current_app.config)
        else:
            return current_app.config['DEFAULT_SERVER']

    def __iter__(self):
        yield 'model', self.model
        yield 'supports', self.supports
        yield 'title', self.title
        if self.default:
            yield 'default', self.default
        if self.domain:
            yield 'domain', self.domain


with open(os.path.join(os.path.dirname(__file__), 'models.json')) as models_json:
    models_cfg = json.load(models_json)

models = Models(models_cfg)



