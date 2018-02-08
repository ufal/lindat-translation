import random
import time
from flask import current_app


def run(english):
    if english:
        import tempfile
        with tempfile.TemporaryFile(delete=False) as temp:
            temp.write(english)
            return '{} '.format(temp.name)
        #import time
        #start_time = time.time()
        #import subprocess
        #subprocess.check_call(['/home/okosarko/run_transformer.sh', '/home/varis/test.in'])
        #seconds = time.time() - start_time
        ##seconds = random.randint(1, current_app.config['MAX_TIME_TO_WAIT'])
    else:
        1 / 0

