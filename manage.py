from uwsgi import app
from flask_script import Server, Manager, Command
from app.db import init_db


manager = Manager(app)
manager.add_command('runserver', Server(host='0.0.0.0', port=5000, use_debugger=True, use_reloader=True))
manager.add_command('init-db', Command(init_db))

if __name__ == '__main__':
    manager.run()
