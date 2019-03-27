from flask import request, url_for
from flask.helpers import  make_response
from flask_restplus import Resource, fields, marshal_with
from flask_restplus.api import output_json

from app.main.api.restplus import api
from app.main.api.translation.parsers import text_input_with_src_tgt # , file_input
from app.model_settings import languages
from app.main.translate import translate_from_to


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


class MyTemplatedUrlField(MyUrlField):

    def __init__(self, params, **kwargs):
        super(MyTemplatedUrlField, self).__init__(required=None, **kwargs)
        self.query_template = '{?' + ','.join(params) + '}'

    def output(self, key, obj, **kwargs):
        url = super(MyTemplatedUrlField, self).output(key, obj, **kwargs)
        return url + self.query_template


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


lang_link = ns.clone('LangLink', link, {
    'href': fields.Url(endpoint='.languages_language_item'),
    'name': fields.String,
    'title': fields.String,
})


def identity(x):
    return x


translate_link =ns.model('TranslateLink', {
        'href': MyTemplatedUrlField(endpoint='.languages_language_collection',
                                    params=['src', 'tgt'], attribute=lambda x: {}),
        'templated': fields.Boolean(attribute=lambda x: True)
    })


# TODO refactor with @api.model? https://flask-restplus.readthedocs.io/en/stable/swagger.html
language_resource = ns.model('LanguageResource', {
    '_links': fields.Nested(
        ns.model('Links', {
            'translate': fields.Nested(translate_link),
            'sources': fields.List(fields.Nested(lang_link, skip_none=True)),
            'targets': fields.List(fields.Nested(lang_link, skip_none=True)),
            'self': fields.Nested(ns.model('JustHrefLink', {
                'href': MyUrlField(endpoint='.languages_language_item', attribute=lambda l: {
                    'language': l.language})
            }), attribute=identity),
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
    _models_item_relation: fields.List(fields.Nested(lang_link, skip_none=True)),
    'self': fields.Nested(link, skip_none=True, attribute=lambda _: {}),
    'translate': fields.Nested(translate_link),
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

    @ns.doc(model=languages_resources)  # This shouldn't be necessary according to docs,
    # but without it the swagger.json does not contain the definitions part
    @marshal_with(languages_resources, skip_none=True)
    def get(self):
        """
        Returns a list of available languages
        """
        values = list(languages.languages.values())
        return {
            '_links': {
                _models_item_relation: values
            },
            '_embedded': {
                _models_item_relation: values
            },
        }

    @ns.produces(['application/json', 'text/plain'])
    @ns.expect(text_input_with_src_tgt, validate=True)
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
    @ns.doc(model=language_resource)  # This shouldn't be necessary according to docs,
    # but without it the swagger.json does not contain the definitions part
    @marshal_with(language_resource, skip_none=True)
    def get(self, language):
        """
        Returns a language resource object
        """
        return languages.languages[language]

