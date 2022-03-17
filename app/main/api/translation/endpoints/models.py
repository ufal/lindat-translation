from flask import request, url_for
from flask_restplus import Resource, fields

from app.main.api.restplus import api
from app.main.api.translation.endpoints.MyAbstractResource import MyAbstractResource
from app.main.api.translation.parsers import text_input_with_src_tgt
from app.model_settings import models
from app.main.translate import translate_with_model
from app.db import log_translation

from app.main.api_examples.model_resource_example import *
from app.main.api_examples.models_resource_example import *


ns = api.namespace('models', description='Operations related to translation models')

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


def identity(x):
    return x


def add_href(model):
    model.add_href(url_for('.models_model_item', model=model.model))
    return model


def get_templated_translate_link(model):
    params = ['src', 'tgt']
    url = url_for('.models_model_item', model=model).rstrip('/')
    query_template = '{?' + ','.join(params) + '}'
    return {'href': url + query_template, 'templated': True}


# TODO refactor with @api.model? https://flask-restplus.readthedocs.io/en/stable/swagger.html
model_resource = ns.model('ModelResource', {
    '_links': fields.Nested(ns.model('ModelResourceLinks', {
        'self': fields.Nested(link, attribute=lambda x: {'href': url_for(
            '.models_model_item', model=x.model)}, skip_none=True),
        'translate': fields.Nested(link, attribute=lambda x: get_templated_translate_link(x.model),
                                   skip_none=True)
    }), attribute=identity, example=model_resource_links_example),
    'default': fields.Boolean(example=True),
    'domain': fields.String(example="Domain name is usually empty"),
    'model': fields.String(required=True, example='en-cs'),
    'supports': fields.Raw(required=True, example={'en': ['cs']}),
    'title': fields.String(example="en-cs (English->Czech (CUBBITT))"),
})

models_links = ns.model('ModelLinks', {
    _models_item_relation: fields.List(fields.Nested(link, skip_none=True), attribute='models'),
    'self': fields.Nested(link, skip_none=True)
})

models_resources = ns.model('ModelsResource', {
    '_links': fields.Nested(models_links,
                            attribute=lambda x: {'self':
                                                 {'href': url_for('.models_model_collection')},
                                                 'models': list(map(add_href, x['models']))},
                            example=models_resource_links_example
                            ),
    '_embedded': fields.Nested(ns.model('EmbeddedModels', {
        _models_item_relation: fields.List(fields.Nested(model_resource, skip_none=True),
                                        attribute='models')
    }), attribute=identity, example=models_resource_embedded_example)
})


@ns.route('/')
class ModelCollection(Resource):

    @ns.marshal_with(models_resources, skip_none=True, code=200, description='Success')
    def get(self):
        """
        Returns a list of available models
        """
        return {'models': models.get_models()}


# TODO should expose templated urls in hal?
@ns.route('/<any' + str(tuple(models.get_model_names())) + ':model>')
@ns.param(**{'name': 'model', 'description': 'model name', 'x-example': 'en-cs', '_in': 'path'})
class ModelItem(MyAbstractResource):

    @ns.produces(['application/json', 'text/plain'])
    @ns.response(code=200, description="Success", model=str)
    @ns.response(code=415, description="You sent a file but it was not text/plain")
    @ns.param(**{'name': 'tgt', 'description': 'tgt query param description', 'x-example': 'cs'})
    @ns.param(**{'name': 'src', 'description': 'src query param description', 'x-example': 'en'})
    @ns.param(**{'name': 'input_text', 'description': 'text to translate',
                 'x-example': 'this is a sample text', '_in': 'formData'})
    def post(self, model):
        """
        Send text to be processed by the selected model.
        It expects the text in variable called `input_text` and handles both "application/x-www-form-urlencoded" and "multipart/form-data" (for uploading text/plain files)
        If you don't provide src or tgt some will be chosen for you!
        """
        text = self.get_text_from_request()
        args = text_input_with_src_tgt.parse_args(request)
        # map model name to model obj
        model = models.get_model(model)
        src_default = list(model.supports.keys())[0]
        src = args.get('src', src_default) or src_default
        if src not in model.supports.keys():
            api.abort(code=404,
                      message='This model does not support translation from {}'
                      .format(src))
        tgt_default = list(model.supports[src])[0]
        tgt = args.get('tgt', tgt_default) or tgt_default
        if tgt not in model.supports[src]:
            api.abort(code=404,
                      message='This model does not support translation from {} to {}'
                      .format(src, tgt))

        author = args.get('author', 'unknown')
        frontend = args.get('frontend', 'unknown')
        log_input = args.get('logInput', False)
        ip_address = request.headers.get('X-Real-IP', 'unknown')
        translation = ''

        self.set_media_type_representations()
        try:
            translation = translate_with_model(model, text, src, tgt)
            return self.create_response(translation,
                                        'src={};tgt={};model={}'.format(src, tgt, model.name))
        finally:
            try:
                if log_input:
                    log_translation(src_lang=src, tgt_lang=tgt, src=text, tgt=' '.join(translation).replace('\n ', '\n'), author=author, frontend=frontend, ip_address=ip_address)
            except:
                pass

    @ns.marshal_with(model_resource, skip_none=True)
    def get(self, model):
        """
        Get model's details
        """
        return models.get_model(model)

