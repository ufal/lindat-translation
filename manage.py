from uwsgi import app


#manager.add_command('runserver', Server(host='0.0.0.0', port=5000, use_debugger=True, use_reloader=True))
#flask run -A manage.py --host 0.0.0.0 --port 5000 --debug

@app.cli.command("init-db")
def init_db_command():
    from app.db import init_db
    init_db()
