from flask import Blueprint, render_template, request, session, jsonify, current_app, g, url_for, \
    abort

from .forms import TranslateForm
from ..logging_utils import logged
from app.model_settings import models as models_conf

bp = Blueprint('main', __name__)


@bp.route('/', methods=['GET'])
def index():
    # TODO json index?
    # if _request_wants_json():
    #    return api_index()
    form = TranslateForm()
    form.models.choices = url_for_choices()
    form.models.default = form.models.choices[0][0]

    sources = list(set([(url_for('api.languages_language_item', language=direction[0]),
                         direction[0]) for direction in models_conf.get_possible_directions()]))

    form.source.choices = sources
    form.target.choices = [(l, l) for l in models_conf.get_reachable_langs(sources[0][1])['to']]
    return render_template('index.html', form=form,
                           file_size_limit=current_app.config['MAX_CONTENT_LENGTH'])


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
