import sys
sys.path.append('/home/varis/tensor2tensor-1.6.6/')
sys.path.append('/home/varis/tensorflow-virtualenv/lib/python3.5/site-packages/')
from flask import g, request
from flask_restplus import abort
from app.factory import create_app

app = create_app()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.before_request
def block_old_clients():
    http_x_app_version = request.headers.get('X-App-Version')
    if http_x_app_version == '0.8.0':
        abort(501, 'This app version is not supported, update your app.', title='Unsupported app version')