import os

BOOTSTRAP_SERVE_LOCAL = True
ERROR_404_HELP = False
RESTX_MASK_SWAGGER = False

# These should match with the appropriate constants in the frontend
# Maximum uploaded file size length is checked by Flask: https://flask.palletsprojects.com/en/2.3.x/patterns/fileuploads/#improving-uploads
MAX_CONTENT_LENGTH = 5 * 1024 * 1024
# Maximum text length inside the uploaded file
MAX_TEXT_LENGTH = 100 * 1024

BATCH_SIZE = 20 #1000
MARIAN_BATCH_SIZE = 16
SENT_LEN_LIMIT = 500
#CSRF prevention
SECRET_KEY = (os.environ.get('SECRET_KEY') or
              b'\x0c\x11{\xd3\x11$\xeeel\xa6\xfb\x1d~\xfd\xb3\x9d\x11\x00\xfb4\xd64\xd4\xe0')
#DEFAULT_SERVER = 'localhost:9000'
#DEFAULT_SERVER = '10.10.51.30:9000'
#T2T_TRANSFORMER2 = '10.10.51.31:9000'
#MARIAN = '10.10.51.50'
DEFAULT_SERVER = '10.10.51.71:9000'
GPU2 = '10.10.51.72:9000'
GPU3 = '10.10.51.73:9000'
ENCS_LOAD_BALANCED = '10.10.51.71:9000'
CSEN_LOAD_BALANCED = '10.10.51.72:9000'
DOCLVL_LOAD_BALANCED = '10.10.51.76:9000'

UPLOAD_FOLDER = '/tmp/translator_uploads'

# These should match with the appropriate constants in the frontend
ALLOWED_EXTENSIONS = {'txt', 'xml', 'html', 'htm', 'docx', 'odt', 'pptx', 'odp', 'xlsx', 'ods', 'pdf'}
