from flask_script import Server, Manager
from uwsgi import app
import sys
sys.path.append('/home/varis/tensor2tensor-1.6.6/')


manager = Manager(app)
manager.add_command('runserver', Server(host='0.0.0.0', port=5000, use_debugger=True, use_reloader=True))

if __name__ == '__main__':
    manager.run()
