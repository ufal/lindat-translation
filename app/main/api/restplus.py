from flask import render_template
from flask_restx import Api

# TODO terms, etc.
api = Api(version='2.0', title='LINDAT Translation API', default_mediatype=None,
          contact_email='lindat-technical@ufal.mff.cuni.cz', doc='/doc')


@api.documentation
def custom_ui():
    return render_template('swagger-ui.html', title=api.title,
                           specs_url=api.specs_url)
