from flask import Blueprint, render_template, url_for, flash, redirect
from .. import tasks
from forms import TaskForm

bp = Blueprint('main', __name__)


@bp.route('/', methods=['GET', 'POST'])
def index():
    form = TaskForm()
    if form.validate_on_submit():
        task = form.task.data
        try:
            result = tasks.run(task)
        except Exception as e:
            flash('Task failed: {}'.format(e), 'danger')
        else:
            flash(result, 'success')
        return redirect(url_for('main.index'))
    return render_template('index.html', form=form)
