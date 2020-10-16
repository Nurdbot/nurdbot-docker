FROM python:3.8

ENV APP_HOME / app
WORKDIR $APP_HOME
COPY . ./

RUN pip install -r requirments.txt


CMD exec python twitch.py

