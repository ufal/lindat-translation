import random
import time
from flask import current_app


def run(task):
    if 'error' in task:
        time.sleep(0.5)
        1 / 0
    if task.startswith('Short'):
        seconds = 1
        time.sleep(seconds)
    else:
        import time
        start_time = time.time()
        import subprocess
        subprocess.check_call(['/home/okosarko/run_transformer.sh', '/home/varis/test.in'])
        seconds = time.time() - start_time
        #seconds = random.randint(1, current_app.config['MAX_TIME_TO_WAIT'])
    return '{} performed in {} second(s)'.format(task, seconds)
