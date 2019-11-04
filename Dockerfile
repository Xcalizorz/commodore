FROM docker.io/python:3.6.9-slim-buster AS base

FROM base AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y make build-essential && apt-get clean
RUN pip install pipenv

ENV PIPENV_VENV_IN_PROJECT=1

COPY Pipfile Pipfile.lock ./

RUN chown -R 1001 /app
USER 1001

RUN pipenv install

FROM docker.io/golang:1.12-stretch AS helm_binding_builder

RUN apt-get update && apt-get install -y python3-cffi && apt-get clean

WORKDIR /virtualenv
COPY --from=builder /app/.venv/lib/python3.6/site-packages/kapitan ./kapitan
RUN ./kapitan/inputs/helm/build.sh

FROM base

WORKDIR /app
RUN apt-get update && apt-get install -y git libnss-wrapper && apt-get clean

RUN pip install pipenv

ENV PIPENV_VENV_IN_PROJECT=1

COPY --from=builder /app/.venv/ ./.venv/
COPY --from=helm_binding_builder \
	/virtualenv/kapitan/inputs/helm/libtemplate.so \
	/virtualenv/kapitan/inputs/helm/helm_binding.py \
	./.venv/lib/python3.6/site-packages/kapitan/inputs/helm/

COPY . ./

RUN ssh-keyscan -t rsa git.vshn.net > /app/.known_hosts

ENV GIT_SSH=/app/tools/ssh

RUN chown 1001 /app
USER 1001

ENTRYPOINT ["pipenv", "run", "commodore"]
