from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField, BooleanField, validators


class TranslateForm(FlaskForm):
    lang_pair = SelectField(label="Language pair", validators=[validators.data_required()])
    models = SelectField(label="Models", render_kw={'class_': 'hidden'})
    source = SelectField(label="Source", render_kw={'class_': 'hidden'})
    target = SelectField(label="Target", render_kw={'class_': 'hidden'})
    advanced = BooleanField(label="advanced")
    input_text = TextAreaField(label='Input sentences', validators=[validators.data_required()],
                               render_kw={'rows': 10})
    output_text = TextAreaField(label='Translation', render_kw={'rows': 10, 'disabled': True})

    def __init__(self, *args, **kwargs):
        super(TranslateForm, self).__init__(*args, **kwargs)
