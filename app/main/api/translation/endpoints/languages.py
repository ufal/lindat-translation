from flask import request, url_for
from flask_restplus import Resource, fields, marshal_with

from app.main.api.restplus import api
from app.main.api.translation.parsers import text_input_with_src_tgt # , file_input
from app.model_settings import models
from app.main.translate import translate_from_to
from app.main.api.translation.endpoints.models import model_link
# from six.moves.urllib.parse import urlparse, urlunparse
# TODO refactor
from app.main.views import _request_wants_json


class MyUrlField(fields.Url):

    def output(self, key, obj, **kwargs):
        try:
            data = fields.to_marshallable_type(fields.get_value(key if self.attribute is None
                                                                else self.attribute, obj))
            endpoint = self.endpoint if self.endpoint is not None else request.endpoint
            o = fields.urlparse(url_for(endpoint, _external=self.absolute, **data))
            path = o.path  # .rstrip('/')
            if self.absolute:
                scheme = self.scheme if self.scheme is not None else o.scheme
                netloc = o.netloc
            else:
                scheme = ""
                netloc = ""
            return fields.urlunparse((scheme, netloc, path, "", o.query, ""))
        except TypeError as te:
            raise fields.MarshallingError(te)


ns = api.namespace('languages', description='Operations with source and target languages')

_models_item_relation = 'item'

link = ns.model('Link', {
    'href': fields.Url,
    'name': fields.String,
    'title': fields.String,
    'type': fields.String,
    'deprecation': fields.String,
    'profile': fields.String,
    'templated': fields.String,
    'hreflang': fields.String
})

# resource = ns.model('Resource', {
#    '_links': fields.List(fields.Nested(link, skip_none=True)),
#    '_embedded': fields.List(fields.Nested(resource))
#})


def rem_title_from_dict(aDict):
    ret = dict(aDict)
    ret.pop('title', None)
    return ret


lang_link = ns.clone('LangPairLink', link, {
    'href': MyUrlField(endpoint='.languages_language_collection', attribute=rem_title_from_dict),
    'name': fields.String(attribute='model'),
})


def identity(x):
    return x


# TODO refactor with @api.model? https://flask-restplus.readthedocs.io/en/stable/swagger.html
language_resource = ns.model('LanguageResource', {
    '_links': fields.Nested(
        ns.model('Links', {
            'self': fields.Nested(ns.model('JustHrefLink', {
                'href': MyUrlField(endpoint='.languages_language_collection',
                                   attribute=rem_title_from_dict)
            }), attribute=identity),
            'models': fields.List(fields.Nested(model_link, skip_none=True),
                                  attribute=lambda x: [m for m in models.get_model_list(x['src'],
                                                                                        x['tgt'])]),
        }), attribute=identity),
    'source': fields.String(attribute='src'),
    'target': fields.String(attribute='tgt'),
    'title': fields.String,
})

languages_links = ns.model('LanguageLinks', {
    _models_item_relation: fields.List(fields.Nested(lang_link, skip_none=True),
                                       attribute='languages'),
    'self': fields.Nested(link, skip_none=True)
})

languages_resources = ns.model('LanguagesResource', {
    '_links': fields.Nested(languages_links, attribute=lambda x: {'self': {}, 'languages': x[
        'languages']}),
    '_embedded': fields.Nested(ns.model('EmbeddedLanguages', {
        _models_item_relation: fields.List(fields.Nested(language_resource, skip_none=True),
                                           attribute='languages')
    }), attribute=identity)
})


@ns.route('/')
class LanguageCollection(Resource):

    @classmethod
    def to_text(cls, data, code, headers):
        resp = api.make_response(' '.join(data).replace('\n ', '\n'), code)
        resp.headers.extend(headers)
        return resp

    # TODO fix in browser get languages (text/plain) returns crap
    # TODO also jquery ajax for some reason receives text/plain instead of json
    #def __init__(self, const_api=None, *args, **kwargs):
    #    super(LanguageCollection, self).__init__(const_api, *args, **kwargs)
    #    self.representations = self.representations if self.representations else {}
    #    self.representations['text/plain'] = LanguageCollection.to_text

    @ns.doc(model=languages_resources)  # This shouldn't be necessary according to docs,
    # but without it the swagger.json does not contain the definitions part
    @marshal_with(languages_resources, skip_none=True)
    def get(self):
        """
        Returns a list of available models
        """
        return {'languages': [{'title': x[2], 'src': x[0], 'tgt': x[1]} for x in
                              models.get_possible_directions()]}

    @ns.produces(['application/json', 'text/plain'])
    @ns.expect(text_input_with_src_tgt, validate=True)
    def post(self):
        """
        Send text to be processed by the selected model.
        It expects the text in variable called `input_text` and handles both "application/x-www-form-urlencoded" and "multipart/form-data" (for uploading text/plain files)
        """
        if request.files and 'input_text' in request.files:
            input_file = request.files.get('input_text')
            if input_file.content_type != 'text/plain':
                api.abort(code=415, message='Can only handle text/plain files.')
            text = input_file.read().decode('utf-8')
        else:
            text = request.form.get('input_text')
        args = text_input_with_src_tgt.parse_args(request)
        src = args.get('src', 'en')
        tgt = args.get('tgt', 'cs')
        return translate_from_to(src, tgt, text)

