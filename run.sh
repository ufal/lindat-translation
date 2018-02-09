#1/bin/bash
source virtualenv/bin/activate
nohup python manage.py runworker &
nohup python manage.py runserver &

