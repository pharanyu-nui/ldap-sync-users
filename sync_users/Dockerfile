
FROM python:3.8.12-alpine3.14

WORKDIR /opt/app

COPY ./requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN crontab crontab

CMD ["crond", "-f"]