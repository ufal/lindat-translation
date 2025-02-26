import logging
from flask import request, url_for
from flask_restx import Namespace, Resource, fields

from app.main.api.translation.endpoints.MyAbstractResource import MyAbstractResource
from app.main.api.translation.parsers import text_input_with_src_tgt  # , file_input
from app.model_settings import languages

from app.main.api_examples.language_resource_example import *
from app.main.api_examples.languages_resource_example import *

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

ns = Namespace('languages', description='Operations with source and target languages')

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
        }), attribute=identity, example=language_resource_links_example),
    'name': fields.String(example='cs'),
    'title': fields.String(example="Czech"),
})

languages_links = ns.model('LanguageLinks', {
    _models_item_relation: fields.List(fields.Nested(link, skip_none=True)),
    'self': fields.Nested(link, skip_none=True, attribute=lambda _: {'href': url_for(
        '.languages_language_collection')}),
    'translate': fields.Nested(link, attribute=lambda _: get_templated_translate_link(),
                               skip_none=True),
})

languages_resources = ns.model('LanguagesResource', {
    '_links': fields.Nested(languages_links, example=languages_resource_links_example),
    '_embedded': fields.Nested(ns.model('EmbeddedLanguages', {
        _models_item_relation: fields.List(fields.Nested(language_resource, skip_none=True))
    }), example=languages_resource_embedded_example)
})

@ns.route('/')
class LanguageCollection(Resource):
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


@ns.route('/')
class LanguageTranslate(MyAbstractResource):
    @ns.produces(['application/json', 'text/plain'])
    @ns.response(code=200, description="Success", model=str)
    @ns.response(code=415, description="Unsupported file type for translation")
    @ns.param(**{'name': 'tgt', 'description': 'tgt query param description', 'x-example': 'cs'})
    @ns.param(**{'name': 'src', 'description': 'src query param description', 'x-example': 'en'})
    @ns.param(**{'name': 'input_text', 'description': 'text to translate',
                 'x-example': 'this is a sample text', '_in': 'formData'})
    def post(self):
        """
        Translate input from scr lang to tgt lang.
        It expects the text in variable called `input_text` and handles both "application/x-www-form-urlencoded" and "multipart/form-data" (for uploading files)
        """
        self.start_time_request()
        translatable = self.get_translatable_from_request()
        args = text_input_with_src_tgt.parse_args(request)
        src = args.get('src') or 'en'
        tgt = args.get('tgt') or 'cs'
        self.set_media_type_representations()
        try:
            translatable.translate_from_to(src, tgt)
            extra_msg = 'src={};tgt={}'.format(src, tgt)
            return translatable.create_response(self.extra_headers(extra_msg))
        except ValueError as e:
            log.exception(e)
            ns.abort(code=404, message='Can\'t translate from {} to {}'.format(src, tgt))
        finally:
            try:
                self.log_request(src, tgt, translatable)
            except Exception as ex:
                log.exception(ex)


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

