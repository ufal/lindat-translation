import os
from flask import Blueprint, render_template, request, jsonify, current_app, g, url_for, abort
from .forms import TaskForm, FileForm
import tensorflow as tf
from tensor2tensor.serving import serving_utils
from tensor2tensor.utils import registry, usr_dir
from sentence_splitter import split_text_into_sentences

usr_dir.import_usr_dir('~varis/t2t_usr_dir')
problem = registry.problem('translate_encs_wmt_czeng57m32k')
hparams = tf.contrib.training.HParams(data_dir=os.path.expanduser('~varis/t2t_data_dir'))
problem.get_hparams(hparams)


bp = Blueprint('main', __name__)
_choices = [('en-cs', 'English->Czech'), ('cs-en', 'Czech->English')]
_models = list(map(lambda pair: pair[0], _choices))


def _translate(model, text):
    request_fn = serving_utils.make_grpc_request_fn(servable_name=model + '_model',
                                                    server='10.10.51.30:9000', timeout_secs=500)
    lang = model.split('-')[0]
    sentences = []
    newlines_after = []
    for segment in text.split('\n'):
        if segment:
            sentences += split_to_sent_array(segment, lang=lang)
        newlines_after.append(len(sentences)-1)
    outputs = list(map(lambda sent_score: sent_score[0],
                       serving_utils.predict(sentences, problem, request_fn)))
    for i in newlines_after:
        if i >= 0:
            outputs[i] += '\n'
    return outputs


@bp.route('/', methods=['GET'])
def index():
    if _request_wants_json():
        return api_index()
    form = TaskForm()
    choices = url_for_choices()
    form.lang_pair.choices = choices
    form.lang_pair.default = choices[0][0]
    return render_template('index.html', form=form,
                           file_size_limit=current_app.config['MAX_CONTENT_LENGTH'])


@bp.route('/translate/upload', methods=['GET', 'POST'])
def upload():
    file_form = FileForm()
    choices = url_for_choices()
    file_form.lang_pair.choices = _choices
    file_form.lang_pair.default = _choices[0][0]
    if file_form.validate_on_submit():
        input_text = file_form.data_file.data.read().decode('utf-8')
        return str(_translate(file_form.lang_pair.data, input_text))
    return render_template('upload.html', file_form=file_form,
                           file_size_limit=current_app.config['MAX_CONTENT_LENGTH'])


@bp.route('/docs', methods=['GET'])
def docs():
    return render_template('docs.html', file_size_limit=current_app.config['MAX_CONTENT_LENGTH'])


def url_for_choices():
    return list(map(lambda choice: (url_for('main.run_task', model=choice[0]), choice[1]), _choices))


def split_to_sent_array(text, lang):
    return split_text_into_sentences(text=text, language=lang)


def _request_wants_json():
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']


@bp.route('/api', methods=['GET'])
def api_index():
    return jsonify({
        '_links': {
            'self': {'href': url_for('main.api_index')},
            'versions': [{'href': url_for('main.api_index_v1'), 'title': 'Version 1'}],
            'latest': {'href': url_for('main.api_index_v1'), 'title': 'Version 1'}
        },
        '_embedded': {
            'latest': index_v1()
        }
    })


@bp.route('/api/v1')
def api_index_v1():
    return jsonify(index_v1())


def index_v1():
    return {
        '_links': {
            'self': {'href': url_for('main.api_index_v1')},
            'models': {'href': url_for('main.api_models_v1')}
        },
        '_embedded': {
            'models': models()
        }
    }


@bp.route('/api/v1/models', methods=['GET'])
def api_models_v1():
    return jsonify(models())


def models():
    return {
        '_links': {
            'self': url_for('main.api_models_v1'),
            'models': [{'href': choice[0], 'title': choice[1]} for choice in
                               url_for_choices()]
        }
    }


@bp.route('/api/v1/models/<any' + str(tuple(_models)) + ':model>', methods=['POST'])
def run_task(model):
    if request.files and 'input_text' in request.files:
        input_file = request.files.get('input_text')
        if input_file.content_type != 'text/plain':
            abort(415)
        text = input_file.read().decode('utf-8')
    else:
        text = request.form.get('input_text')
    outputs = _translate(model, text)
    if _request_wants_json():
        return jsonify(outputs)
    else:
        return str(outputs)


