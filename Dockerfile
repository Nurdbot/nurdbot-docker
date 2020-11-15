FROM python:3.9-buster

ENV APP_HOME / app
WORKDIR $APP_HOME
COPY . ./

RUN pip3 install -r requirments.txt



CMD [ "python3","-u", "twitch.py" ]
