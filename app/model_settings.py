import json
import logging
import os
from iso639 import to_name
import networkx as nx

from app.dict_utils import get_or_create
from app.models import Model

log = logging.getLogger(__name__)


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
            model = Model.create(cfg)
            if model.model in self._models:
                log.error("Model names should be unique")
                import sys
                sys.exit(1)
            self._models[model.model] = model
            if cfg.get('default'):
                _default_model_name = cfg['model']

            if cfg.get('include_in_graph', True):
                flip_src_tgt = cfg.get('target_to_source', False)
                for src_lang in cfg['source']:
                    for tgt_lang in cfg['target']:
                        weight = cfg.get('weight', 1)
                        # This will keep only the last model
                        self._G.add_edge(src_lang, tgt_lang, cfg=model, weight=weight)
                        if flip_src_tgt:
                            self._G.add_edge(tgt_lang, src_lang, cfg=model, weight=weight)

        # There may be more than one shortest path between source and target; this returns only one
        self._shortest_path = dict(nx.all_pairs_dijkstra_path(self._G, cutoff=2))
        _directions = []
        self._src_tgt = {}
        self._tgt_src = {}
        for item in self._shortest_path.items():
            u = item[0]
            for v in item[1].keys():
                if u != v:
                    display = '{}->{}'.format(to_name(u), to_name(v))
                    _directions.append((u, v, display))
                    targets = get_or_create(self._src_tgt, u)
                    targets.append(v)
                    sources = get_or_create(self._tgt_src, v)
                    sources.append(u)
        self._directions = sorted(_directions, key=lambda x: x[2])

    def get_possible_directions(self):
        return self._directions

    def get_reachable_langs(self, lang):
        where_lang_is_src = self._src_tgt.get(lang, [])
        where_lang_is_tgt = self._tgt_src.get(lang, [])
        return {
            'name': lang,
            'title': to_name(lang),
            'to': where_lang_is_src,
            'from': where_lang_is_tgt
        }

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
                return [{
                    'model': self._G[pair[0]][pair[1]]['cfg'],
                    'src': pair[0],
                    'tgt': pair[1],
                } for pair in zip(path[0:-1], path[1:])]
            else:
                return []
        except KeyError as e:
            return []

    def get_default_model_name(self):
        return self._default_model_name

    def get_model_names(self):
        return list(self._models.keys())

    def get_models(self):
        return list(self._models.values())

    def get_model(self, model_name):
        return self._models.get(model_name, self._models.get(self.get_default_model_name()))


class Language(object):

    def __init__(self, iso_code):
        self.language = iso_code
        self.name = iso_code
        self.title = to_name(iso_code)
        self.sources = set()
        self.targets = set()

    def __iter__(self):
        yield 'language', self.language
        yield 'name', self.name
        yield 'title', self.title
        yield 'sources', self.sources
        yield 'targets', self.targets
        if self.href:
            yield 'href', self.href

    def add_href(self, href):
        self.href = href


class Languages(object):

    def __init__(self, models):
        self.languages = {}
        for x in models.get_possible_directions():
            get_or_create(self.languages, x[0], lambda: Language(x[0]))
            get_or_create(self.languages, x[1], lambda: Language(x[1]))

        for iso_code, lang in self.languages.items():
            x = models.get_reachable_langs(iso_code)
            for to_iso_code in x['to']:
                to_lang = self.languages[to_iso_code]
                lang.targets.add(to_lang)
                to_lang.sources.add(lang)
            for from_iso_code in x['from']:
                from_lang = self.languages[from_iso_code]
                lang.sources.add(from_lang)
                from_lang.targets.add(lang)


with open(os.path.join(os.path.dirname(__file__), 'models.json')) as models_json:
    models_cfg = json.load(models_json)

models = Models(models_cfg)
languages = Languages(models)
