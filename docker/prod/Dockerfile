FROM python:3.8-slim-buster

RUN apt-get update
RUN apt-get install -y --no-install-recommends gfortran
RUN pip3 install uwsgi

COPY ./requirements.txt /mergeminion/requirements.txt

RUN pip3 install -r /mergeminion/requirements.txt

COPY . /mergeminion

WORKDIR /mergeminion

CMD ["uwsgi", "--ini","uwsgi.ini"]
