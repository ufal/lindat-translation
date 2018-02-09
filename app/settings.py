import os

BOOTSTRAP_SERVE_LOCAL = True
#CSRF prevention
SECRET_KEY = (os.environ.get('SECRET_KEY') or
              b'\x0c\x11{\xd3\x11$\xeeel\xa6\xfb\x1d~\xfd\xb3\x9d\x11\x00\xfb4\xd64\xd4\xe0')
TASKS = ['Short task', 'Long task', 'Task raises error']
MAX_TIME_TO_WAIT = 10
REDIS_URL = 'redis://localhost:6379/11'
QUEUES = ['default']
