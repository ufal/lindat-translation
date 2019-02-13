import logging
from flask import Flask, Blueprint
from . import settings
from .extensions import bootstrap
from .main.views import bp as main
from app.main.api.restplus import api
from app.main.api.translation.endpoints.models import ns as models_ns


class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the 
    front-end server to add these headers, to let you quietly bind 
    this to a URL other than / and to an HTTP scheme that is 
    different than what is used locally.

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    '''
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


def create_app():
    app = Flask(__name__)
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.config.from_object(settings)
    app.config.from_envvar('LOCAL_SETTINGS', silent=True)
    logging.getLogger().error('DEFAULT_SERVER=' + app.config.get('DEFAULT_SERVER'))
    bootstrap.init_app(app)
    app.register_blueprint(main)

    api_bp = Blueprint('api', __name__, url_prefix='/api/v2')
    api.init_app(api_bp)
    api.add_namespace(models_ns)
    app.register_blueprint(api_bp)
    return app;
