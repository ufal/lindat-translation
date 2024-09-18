FROM ubuntu:22.04 AS tikal
RUN sed -i -e 's# http://[^ ]* # http://ftp.cvut.cz/ubuntu/ #' /etc/apt/sources.list
RUN apt-get update && apt-get install -y curl unzip
WORKDIR /tmp
RUN curl -LJO https://okapiframework.org/binaries/main/1.46.0/okapi-apps_gtk2-linux-x86_64_1.46.0.zip && mkdir okapi-apps && cd okapi-apps && unzip /tmp/okapi-apps_gtk2-linux-x86_64_1.46.0.zip

FROM ubuntu:22.04

COPY --from=tikal /tmp/okapi-apps /srv/okapi-apps

# python & pygame dependencies
RUN sed -i -e 's# http://[^ ]* # http://ftp.cvut.cz/ubuntu/ #' /etc/apt/sources.list
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
      python3 python3-pip python3-venv \
      git \
      openjdk-21-jre-headless \
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
COPY requirements_freeze.txt requirements.txt
ENV VIRTUAL_ENV=/srv/transformer_frontend/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install --upgrade pip==21 wheel==0.38.0 setuptools==65.5.1 && \
    pip install -r requirements.txt
COPY . .

RUN ln -fs /srv/transformer_frontend/app/static/lindat-common/ app/templates/lindat-common
RUN flask --app manage.py init-db

EXPOSE 5000
ENTRYPOINT ["/srv/transformer_frontend/venv/bin/gunicorn", "-t", "500", "-k", "sync", "-w", "3", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--access-logformat", "%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\" %({http_accept}e)s %({accept}i)s" , "uwsgi:app"]

#ENTRYPOINT [ "/srv/transformer_frontend/venv/bin/flask", "--app", "manage.py", "run", "--debug", "--host", "0.0.0.0", "--port", "5000" ]
