from flask import request, url_for
from flask_restplus import Resource, fields, marshal_with

from app.main.api.restplus import api
from app.main.api.translation.parsers import text_input_with_src_tgt #text_input # , file_input
from app.model_settings import models
from app.main.translate import translate_with_model


ns = api.namespace('models', description='Operations related to translation models')

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

model_link = ns.clone('ModelLink', link, {
    'href': fields.Url(endpoint='.models_model_item'),
    'name': fields.String(attribute='model'),
})


def identity(x):
    return x


# TODO refactor with @api.model? https://flask-restplus.readthedocs.io/en/stable/swagger.html
model_resource = ns.model('ModelResource', {
    '_links': fields.Nested(ns.model('SelfLink', {
        'self': fields.Nested(ns.model('JustHrefLink', {'href': fields.Url(
            endpoint='.models_model_item')}), attribute=identity)
    }), attribute=identity),
    'default': fields.Boolean,
    'domain': fields.String,
    'model': fields.String,
    # TODO is raw ok, how does it look in swagger
    'supports': fields.Raw,
    'title': fields.String,
})

models_links = ns.model('ModelLinks', {
    _models_item_relation: fields.List(fields.Nested(model_link, skip_none=True), attribute='models'),
    'self': fields.Nested(link, skip_none=True)
})

models_resources = ns.model('ModelsResource', {
    '_links': fields.Nested(models_links, attribute=lambda x: {'self': {}, 'models': x['models']}),
    '_embedded': fields.Nested(ns.model('EmbeddedModels', {
        _models_item_relation: fields.List(fields.Nested(model_resource, skip_none=True),
                                        attribute='models')
    }), attribute=identity)
})


@ns.route('/')
class ModelCollection(Resource):

    @ns.doc(model=models_resources)  # This shouldn't be necessary according to docs,
    # but without it the swagger.json does not contain the definitions part
    @marshal_with(models_resources, skip_none=True)
    def get(self):
        """
        Returns a list of available models
        """
        return {'models': models.get_models()}


# TODO should expose templated urls in hal?
@ns.route('/<any' + str(tuple(models.get_model_names())) + ':model>')
class ModelItem(Resource):

    @classmethod
    def to_text(cls, data, code, headers):
        resp = api.make_response(' '.join(data).replace('\n ', '\n'), code)
        resp.headers.extend(headers)
        return resp

    # TODO fix text/plain
    #def __init__(self, const_api=None, *args, **kwargs):
    #    super(ModelItem, self).__init__(const_api, *args, **kwargs)
    #    self.representations = self.representations if self.representations else {}
    #    self.representations['text/plain'] = ModelItem.to_text

    #TODO is there a default src/tgt?
    @ns.produces(['application/json', 'text/plain'])
    @ns.expect(text_input_with_src_tgt, validate=True)
    def post(self, model):
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
        #return ' '.join(translate_with_model(model, text)).replace('\n ', '\n')
        args = text_input_with_src_tgt.parse_args(request)
        src = args.get('src', None)
        tgt = args.get('tgt', None)
        # map model name to model obj
        model = models.get_model(model)
        if src not in model.supports.keys() or tgt not in model.supports[src]:
            api.abort(code=404,
                      message='This model does not support translation from {} to {}'
                      .format(src, tgt))

        return translate_with_model(model, text, src, tgt)

    @marshal_with(model_resource, skip_none=True)
    def get(self, model):
        """
        Get model's details
        """
        return models.get_model(model)

