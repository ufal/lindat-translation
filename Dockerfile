FROM python:3.5

WORKDIR /srv/transformer_frontend
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .

EXPOSE 5000
ENTRYPOINT ["/usr/local/bin/gunicorn", "-t", "500", "-k", "sync", "-w", "3", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--access-logformat", "%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\" %({http_accept}e)s %({accept}i)s" , "uwsgi:app"]
