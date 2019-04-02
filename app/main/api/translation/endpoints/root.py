from flask import url_for
from flask_restplus import Resource, marshal_with, fields
from app.main.api.restplus import api

ns = api.namespace('root', description='Root resource for navigation to languages/models', path='/')


def identity(x):
    return x


link = ns.model('Link', {
    'href': fields.String,
    'name': fields.String,
    'title': fields.String,
    'type': fields.String,
    'deprecation': fields.String,
    'profile': fields.String,
    'templated': fields.String,
    'hreflang': fields.String
})


root_resource = ns.model('RootResource', {
    '_links': fields.Nested(ns.model('Links', {
        'self': fields.Nested(link, attribute=lambda x: {'href': fields.Url(
            '.root_root_resource')}, skip_none=True),
        'models': fields.Nested(link, skip_none=True),
        'languages': fields.Nested(link, skip_none=True)
    }), attribute=identity),
})


@ns.route('/')
class RootResource(Resource):

    @ns.marshal_with(root_resource, skip_none=True, code=200, description="Success")
    def get(self):
        return {
            'models': {
                'href': url_for('api.models_model_collection'),
                'name': 'models'
            },
            'languages': {
                'href': url_for('api.languages_language_collection'),
                'name': 'languages'
            }
        }
