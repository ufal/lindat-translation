from flask import request, url_for
from flask.helpers import make_response
from flask_restplus import Resource, fields
from flask_restplus.api import output_json

from app.main.api.restplus import api
from app.main.api.translation.parsers import text_input_with_src_tgt # , file_input
from app.model_settings import languages
from app.main.translate import translate_from_to


ns = api.namespace('languages', description='Operations with source and target languages')

_models_item_relation = 'item'

link = ns.model('Link', {
    'href': fields.String,
    'name': fields.String,
    'title': fields.String,
    'type': fields.String,
    'deprecation': fields.String,
    'profile': fields.String,
    'templated': fields.Boolean,
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


def identity(x):
    return x


def set_endpoint_href(lang_o):
    def add_href(x):
        x.add_href(url_for('.languages_language_item', language=x.language))
        return x

    lang_o.sources = list(map(lambda src: add_href(src), lang_o.sources))
    lang_o.targets = list(map(lambda tgt: add_href(tgt), lang_o.targets))


def get_templated_translate_link():
    params = ['src', 'tgt']
    url = url_for('.languages_language_collection').rstrip('/')
    query_template = '{?' + ','.join(params) + '}'
    return {'href': url + query_template, 'templated': True}



# TODO refactor with @api.model? https://flask-restplus.readthedocs.io/en/stable/swagger.html
language_resource = ns.model('LanguageResource', {
    '_links': fields.Nested(
        ns.model('LanguageResourceLinks', {
            'translate': fields.Nested(link, attribute=lambda _: get_templated_translate_link(),
                                       skip_none=True),
            'sources': fields.List(fields.Nested(link, skip_none=True)),
            'targets': fields.List(fields.Nested(link, skip_none=True)),
            'self': fields.Nested(link, attribute=lambda x: {'href': url_for(
                '.languages_language_item', language=x.language)}, skip_none=True),
            # TODO potrebuju linky na modely k necemu? Potrebuju, kdyby interface vypadal choose
            #  lang -> choose from models
            #'models': fields.List(fields.Nested(model_link, skip_none=True),
            #                      attribute=lambda x: [m for m in models.get_model_list(x['src'],
            #                                                                            x[
            #                                                                            'tgt'])]),
        }), attribute=identity),
    'name': fields.String,
    'title': fields.String,
})

languages_links = ns.model('LanguageLinks', {
    _models_item_relation: fields.List(fields.Nested(link, skip_none=True)),
    'self': fields.Nested(link, skip_none=True, attribute=lambda _: {'href': url_for(
        '.languages_language_collection')}),
    'translate': fields.Nested(link, attribute=lambda _: get_templated_translate_link(),
                               skip_none=True),
})

languages_resources = ns.model('LanguagesResource', {
    '_links': fields.Nested(languages_links),
    '_embedded': fields.Nested(ns.model('EmbeddedLanguages', {
        _models_item_relation: fields.List(fields.Nested(language_resource, skip_none=True))
    }))
})


@ns.route('/')
class LanguageCollection(Resource):

    @classmethod
    def to_text(cls, data, code, headers):
        return make_response(' '.join(data).replace('\n ', '\n'), code, headers)

    @ns.marshal_with(languages_resources, skip_none=True)
    def get(self):
        """
        Returns a list of available languages
        """
        values = list(languages.languages.values())
        for lang_o in values:
            set_endpoint_href(lang_o)

        return {
            '_links': {
                _models_item_relation: values
            },
            '_embedded': {
                _models_item_relation: values
            },
        }

    @ns.produces(['application/json', 'text/plain'])
    @ns.response(code=200, description="Success", model=str)
    @ns.response(code=415, description="You sent a file but it was not text/plain")
    @ns.param(**{'name': 'tgt', 'description': 'tgt query param description', 'x-example': 'cs'})
    @ns.param(**{'name': 'src', 'description': 'src query param description', 'x-example': 'en'})
    @ns.param(**{'name': 'input_text', 'description': 'text to translate',
                 'x-example': 'this is a sample text', '_in': 'formData'})
    def post(self):
        """
        Translate input from scr lang to tgt lang.
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
        try:
            self.representations = self.representations if self.representations else {}
            if 'text/plain' not in self.representations:
                self.representations['text/plain'] = LanguageCollection.to_text
            if 'application/json' not in self.representations:
                self.representations['application/json'] = output_json
            return translate_from_to(src, tgt, text)
        except ValueError as e:
            api.abort(code=404, message='Can\'t translate from {} to {}'.format(src, tgt))


@ns.route('/<string(length=2):language>')
class LanguageItem(Resource):
    @ns.marshal_with(language_resource, skip_none=True)
    @ns.param(**{'name': 'language', 'description': 'Language code',
                 'x-example': 'en', '_in': 'path'})
    def get(self, language):
        """
        Returns a language resource object
        """
        lang_o = languages.languages[language]
        # TODO can we not call setter when the href was alredy set
        set_endpoint_href(lang_o)
        return lang_o

