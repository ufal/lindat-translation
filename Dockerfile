FROM python:3.8

# pygame dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
      cmake \
      libsdl-image1.2-dev \
      libsdl-mixer1.2-dev \
      libsdl-ttf2.0-dev \
      libsmpeg-dev \
      libsdl1.2-dev \
      libportmidi-dev \
      libswscale-dev \
      libavformat-dev \
      libavcodec-dev \
      libfreetype6-dev && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean


WORKDIR /srv/transformer_frontend
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .

EXPOSE 5000
ENTRYPOINT ["/usr/local/bin/gunicorn", "-t", "500", "-k", "sync", "-w", "3", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--access-logformat", "%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\" %({http_accept}e)s %({accept}i)s" , "uwsgi:app"]
