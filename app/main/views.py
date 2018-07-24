import os
from flask import Blueprint, render_template, request, jsonify, current_app, g, url_for
from .forms import TaskForm
import tensorflow as tf
from tensor2tensor.serving import serving_utils
from tensor2tensor.utils import registry, usr_dir
from sentence_splitter import split_text_into_sentences

usr_dir.import_usr_dir('~varis/t2t_usr_dir')
problem = registry.problem('translate_encs_wmt_czeng57m32k')
hparams = tf.contrib.training.HParams(data_dir=os.path.expanduser('~varis/t2t_data_dir'))
problem.get_hparams(hparams)


bp = Blueprint('main', __name__)


@bp.route('/translate', methods=['POST'])
def run_task():
    text = request.form.get('input_text')
    lang_pair = request.form.get('lang_pair', default='en-cs')
    request_fn = serving_utils.make_grpc_request_fn(servable_name=lang_pair + '_model',
                                                                   server='localhost:9000', timeout_secs=90)
    sentences = split_to_sent_array(text, lang=lang_pair.split('-')[0])
    outputs = list(map(lambda sent_score: sent_score[0],
                       serving_utils.predict(sentences, problem, request_fn)))
    return jsonify(outputs)


@bp.route('/')
def index():
    form = TaskForm()
    return render_template('index.html', form=form)


def split_to_sent_array(text, lang):
    return split_text_into_sentences(text=text, language=lang)
