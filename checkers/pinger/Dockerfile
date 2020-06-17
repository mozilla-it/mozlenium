FROM debian:sid

WORKDIR /app

RUN apt update && \
    apt -y install wget && \
    apt clean

COPY entrypoint.sh /app

ENTRYPOINT [ "/app/entrypoint.sh" ]
