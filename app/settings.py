import os

BOOTSTRAP_SERVE_LOCAL = True
MAX_CONTENT_LENGTH = 32 * 1024
BATCH_SIZE = 1000
#CSRF prevention
SECRET_KEY = (os.environ.get('SECRET_KEY') or
              b'\x0c\x11{\xd3\x11$\xeeel\xa6\xfb\x1d~\xfd\xb3\x9d\x11\x00\xfb4\xd64\xd4\xe0')
