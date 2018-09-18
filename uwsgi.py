import sys
sys.path.append('/home/varis/tensor2tensor-1.6.6/')
sys.path.append('/home/varis/tensorflow-virtualenv/lib/python3.5/site-packages/')
from app.factory import create_app

app = create_app()
