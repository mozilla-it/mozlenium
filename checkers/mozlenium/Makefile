
.DEFAULT_GOAL := build

TAG := $(shell git rev-parse --short HEAD)

build:
	for base in nightly esr chrome; do \
	docker build \
		-t afrank/mozlenium-base:$$base \
		-f Dockerfile.$${base}-base \
		. ; \
	done
	for base in nightly esr; do \
	docker build \
		-t afrank/mozlenium:$$base \
		-f Dockerfile.in \
		--build-arg IMAGE=afrank/mozlenium-base:$$base \
		--build-arg BROWSER=firefox \
		--build-arg NPM_INSTALL=geckodriver \
		. ; \
	done
	for base in chrome; do \
	docker build \
		-t afrank/mozlenium:$$base \
		-f Dockerfile.in \
		--build-arg IMAGE=afrank/mozlenium-base:$$base \
		--build-arg BROWSER=chrome \
		--build-arg NPM_INSTALL=chromedriver \
		. ; \
	done
	for extra in wrapper; do \
	for base in nightly esr chrome; do \
	docker build \
		-t afrank/mozlenium:$${extra}-$$base \
		--build-arg IMAGE=afrank/mozlenium:$$base \
		extras/$$extra ; \
	done ; \
	done
	docker tag afrank/mozlenium:wrapper-nightly afrank/mozlenium:firefox
	docker tag afrank/mozlenium:wrapper-nightly afrank/mozlenium:latest

push:
	for base in nightly esr chrome; do \
		docker push afrank/mozlenium-base:$$base ; \
		docker push afrank/mozlenium:$$base ; \
	done
	for extra in wrapper; do \
	for base in nightly esr chrome; do \
		docker push afrank/mozlenium:$${extra}-$$base ; \
	done ; \
	done
	docker push afrank/mozlenium:firefox
	docker push afrank/mozlenium:latest

