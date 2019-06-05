from flask import Blueprint, render_template, request, current_app, url_for, redirect

from .forms import TranslateForm
from app.model_settings import models as models_conf
from app.model_settings import languages

bp = Blueprint('main', __name__)


@bp.route('/', methods=['GET'])
def index():
    if _request_wants_json():
        return redirect(url_for('api.root_root_resource'))
    form = TranslateForm()
    form.models.choices = url_for_choices()
    form.models.default = form.models.choices[0][0]

    sources = list(sorted(filter(lambda l: l.targets, languages.languages.values()),
                          key=lambda l: l.title))

    default_src = sources[0]

    form.target.choices = sorted([(l.name, l.title) for l in default_src.targets],
                                 key=lambda x: x[1])

    form.source.choices = [(url_for('api.languages_language_item', language=l.name), l.title) for
                           l in sources]
    form.source.data = form.source.choices[0][0]
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
