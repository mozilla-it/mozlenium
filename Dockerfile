FROM python:3

WORKDIR /app

COPY mozalert /app/mozalert
COPY pyproject.toml MANIFEST.in tox.ini setup.cfg /app/

RUN python -m pip install .

ENTRYPOINT  ["mozalert"]
