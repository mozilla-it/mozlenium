FROM debian:sid

WORKDIR /app

RUN apt update && \
    apt -y install curl && \
    apt clean

COPY entrypoint.sh /app

ENTRYPOINT [ "/app/entrypoint.sh" ]
