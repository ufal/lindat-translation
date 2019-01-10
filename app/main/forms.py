from flask import current_app, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SelectField, TextAreaField, SubmitField, BooleanField, validators


class TaskForm(FlaskForm):
    #task = SelectField('Task')
    lang_pair = SelectField(label="Language pair", validators=[validators.data_required()])
    models = SelectField(label="Models", render_kw={'class_': 'hidden'})
    advanced = BooleanField(label="advanced")
    input_text = TextAreaField(label='Input sentences', validators=[validators.data_required()],
                               render_kw={'rows': 10})

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        #self.task.choices = [(task, task) for task in current_app.config['TASKS']]


class FileForm(FlaskForm):
    lang_pair = SelectField(label="Language pair", validators=[validators.data_required()])
    data_file = FileField(label="Text file", validators=[FileRequired(), FileAllowed(['txt'], 'Text files only')])
    translate = SubmitField(label="Translate")

