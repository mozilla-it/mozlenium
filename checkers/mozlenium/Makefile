
.DEFAULT_GOAL := build

TAG := $(shell git rev-parse --short HEAD)

build:
	docker build -t afrank/mozlenium:${TAG} .
	docker tag afrank/mozlenium:${TAG} afrank/mozlenium:latest
push:
	docker push afrank/mozlenium:${TAG}
	docker push afrank/mozlenium:latest

