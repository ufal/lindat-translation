import random
import time
from flask import current_app


def run(english):
    if english:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wt', encoding='utf-8', delete=False) as temp_in:
            temp_in.write(english)
            temp_in.flush()
            output_name = temp_in.name + '_out'
            import subprocess
            subprocess.check_call(['/home/okosarko/run_transformer.sh', temp_in.name, output_name],
                                  timeout=10800)  # 3h
            with open(output_name, mode='rt', encoding='utf-8') as output:
                czech = output.read()
                return czech
            #seconds = time.time() - start_time
            #seconds = random.randint(1, current_app.config['MAX_TIME_TO_WAIT'])
    else:
        1 / 0

