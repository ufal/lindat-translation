import random
import time
from flask import current_app


def run(english):
    if english:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wt', encoding='utf-8', delete=False) as temp:
            temp.write(english)
            temp.flush()
            import subprocess
            subprocess.check_call(['/home/okosarko/run_transformer.sh', temp.name],
                                  timeout=10800)  # 3h
            output_name = temp.name + '.transformer.transformer_big_single_gpu.translate_encs_wmt_czeng57m32k.beam4.alpha0.6.decodes'
            with open(output_name, mode='rt', encoding='utf-8') as output:
                czech = output.read()
                return czech
            #seconds = time.time() - start_time
            #seconds = random.randint(1, current_app.config['MAX_TIME_TO_WAIT'])
    else:
        1 / 0

