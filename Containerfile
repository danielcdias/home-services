FROM python:3.13-slim-trixie

USER root

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV HOME=/home/app
ENV APP_HOME=$HOME/web

RUN mkdir -p $APP_HOME && \
    groupadd app --system && \
    useradd --system app -g app --uid 100 && \
    mkdir $APP_HOME/static && \
    chown -R app:app $HOME

WORKDIR $APP_HOME

RUN apt update && \
    apt upgrade -y && \
    apt install -y speedtest-cli iputils-ping curl && \
    rm -rf /var/lib/apt/lists/* && \
    apt autoclean && \
    apt autoremove

COPY --chown=app:app . .

RUN pip install --no-cache-dir -r requirements.txt && \
    DJANGO_DATABASE_URL="sqlite:///dummy.db" python manage.py collectstatic --no-input && \
    chmod +x ./django-entrypoint.sh

RUN mkdir -p /app/shared && chown -R app:app /app/shared

USER app
