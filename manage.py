import sys
sys.path.append('/home/varis/tensor2tensor-1.6.6/')
sys.path.append('/home/varis/tensorflow-virtualenv/lib/python3.5/site-packages/')
from flask_script import Server, Manager
from uwsgi import app


manager = Manager(app)
manager.add_command('runserver', Server(host='0.0.0.0', port=5000, use_debugger=True, use_reloader=True))

if __name__ == '__main__':
    manager.run()
