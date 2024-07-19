FROM python:3.12-alpine

COPY ./requirements.txt /mergeminion/requirements.txt

RUN pip3 install -r /mergeminion/requirements.txt

COPY . /mergeminion

ENV FLASK_APP=main.py
ENV FLASK_DEBUG=1

WORKDIR /mergeminion

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0", "--port=8000"]

