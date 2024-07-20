FROM python:3.11-alpine

RUN pip3 install uwsgi

COPY ./requirements.txt /mergeminion/requirements.txt

RUN pip3 install -r /mergeminion/requirements.txt

COPY . /mergeminion

WORKDIR /mergeminion

CMD ["uwsgi", "--ini","uwsgi.ini"]
