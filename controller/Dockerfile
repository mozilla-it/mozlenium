FROM python:3

WORKDIR /app

COPY requirements.txt controller.py /app/

RUN python -m pip install -r requirements.txt

ENTRYPOINT  ["/app/controller.py"]
