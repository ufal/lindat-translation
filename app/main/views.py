import redis
from flask import Blueprint, render_template, request, jsonify, current_app, g, url_for
from .. import tasks
from .forms import TaskForm
from rq import push_connection, pop_connection, Queue

bp = Blueprint('main', __name__)


@bp.route('/status/<job_id>')
def job_status(job_id):
    q = Queue()
    job = q.fetch_job(job_id)
    if job is None:
        response = {'status': 'unknown'}
    else:
        response = {
            'status': job.get_status(),
            'result': job.result,
        }
        if job.is_failed:
            response['message'] = job.exec_info.strip().split('\n')[-1]
    return jsonify(response)


@bp.route('/_run_task', methods=['POST'])
def run_task():
    english = request.form.get('english')
    q = Queue()
    job = q.enqueue(tasks.run, english, timeout=10800)
    return jsonify({}), 202, {'Location': url_for('main.job_status', job_id=job.get_id())}


@bp.route('/')
def index():
    form = TaskForm()
    return render_template('index.html', form=form)


def get_redis_connection():
    redis_connection = getattr(g, '_redis_connection', None)
    if redis_connection is None:
        redis_url = current_app.config['REDIS_URL']
        redis_connection = g._redis_connection = redis.from_url(redis_url)
    return redis_connection


@bp.before_request
def push_rq_connection():
    push_connection(get_redis_connection())


@bp.teardown_request
def pop_rq_connection(exception=None):
    pop_connection()
