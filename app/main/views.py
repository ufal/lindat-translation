from flask import Blueprint, render_template, request, session, jsonify, current_app, g, url_for, \
    abort

from .forms import TranslateForm
from ..logging_utils import logged
from app.model_settings import models as models_conf

bp = Blueprint('main', __name__)


@bp.route('/', methods=['GET'])
def index():
    # TODO json index?
    #if _request_wants_json():
    #    return api_index()
    form = TranslateForm()
    choices = get_src_tgt_choices()
    form.lang_pair.choices = choices
    form.lang_pair.default = choices[0][0]
    form.models.choices = url_for_choices()
    form.models.default = form.models.choices[0][0]
    form.source.choices = [('wtf', 'wtf')]
    form.target.choices = [('wtf', 'wtf')]
    return render_template('index.html', form=form,
                           file_size_limit=current_app.config['MAX_CONTENT_LENGTH'])


def url_for_src_tgt(source, target):
    return url_for('api.languages_language_collection', src=source, tgt=target)


def get_src_tgt_choices():
    return list(map(lambda tuple3: (url_for_src_tgt(tuple3[0], tuple3[1]), tuple3[2]),
                    models_conf.get_possible_directions()))


@bp.route('/docs', methods=['GET'])
def docs():
    return render_template('docs.html', file_size_limit=current_app.config['MAX_CONTENT_LENGTH'])


def url_for_choices():
    return list(map(lambda model:
                    (url_for('api.models_model_item', model=model.model), model.title),
                    models_conf.get_models()))


def _request_wants_json():
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']

