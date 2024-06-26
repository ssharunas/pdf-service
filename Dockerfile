FROM python:alpine3.19 AS compiler

WORKDIR /usr/src/app
RUN apk update \
      && apk add --no-cache \
      gcc \
      g++ \
      musl-dev \
      python3-dev \
      jpeg-dev \
      openjpeg-dev \
      zlib-dev \
      libffi-dev \
      openssl-dev \
      pango-dev \
      shared-mime-info \
      build-base

RUN addgroup -S pdf_service_group && \
      adduser --uid 1001 -S pdf_service_user -G pdf_service_group && \
      chown pdf_service_user .
USER pdf_service_user

#RUN pip install --upgrade PyMuPDF==1.20.2
RUN pip install --user --no-cache-dir gunicorn

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:alpine3.19 AS builder

WORKDIR /usr/src/app

RUN apk add --no-cache \
      musl \
      python3 \
      jpeg \
      openjpeg \
      zlib \
      libffi \
      openssl \
      pango \
      # fonts
      ttf-opensans \
      ttf-dejavu \
      font-noto-emoji \
      ghostscript-fonts \
      # Used as the entrypoint
      tini \
      # curl is needed for the status check
      curl

RUN addgroup -S pdf_service_group && \
      adduser --uid 1001 -S pdf_service_user -G pdf_service_group && \
      chown pdf_service_user .
USER pdf_service_user

COPY --from=compiler /home/pdf_service_user/.local/ /home/pdf_service_user/.local/
ENV PATH="/home/pdf_service_user/.local/bin:${PATH}"
ENV PYTHONPATH="/home/pdf_service_user/.local/lib/python3.9/site-packages:${PYTHONPATH}"

# FROM alpine:3.14 AS production_sourcer
# Copy files needed for production image into this step and then copy into a single layer in prod
# image.

# ADD pdf_service .
# ADD

FROM builder AS testing
# Testing stage only for local testing, edit ci.yml test job accordingly.

USER root

RUN apk add --no-cache \
      openssl-dev \
      cargo \
      poppler-utils \
      poppler-dev \
      # For codecov uploader
      bash

USER pdf_service_user

ADD requirements-dev.txt .

RUN pip install --user --no-cache-dir -r requirements-dev.txt

RUN mkdir -p /usr/src/app/coverage
VOLUME /usr/src/app/coverage

COPY . .

ARG GITHUB_SHA
ENV SENTRY_RELEASE=$GITHUB_SHA

FROM builder AS production
# Named stage so it can be optimized in the future. (Stage name is referenced by CI build script.)

COPY pdf_service ./pdf_service
COPY fonts ./fonts

ARG GITHUB_SHA
ENV SENTRY_RELEASE=$GITHUB_SHA

ENV WORKER_COUNT=4

HEALTHCHECK --interval=2s --timeout=2s --retries=5 --start-period=2s CMD curl --fail http://localhost:8080/health || exit 1

CMD tini gunicorn -w $WORKER_COUNT -t 0 -b 0.0.0.0:8080 pdf_service:pdf_service
EXPOSE 8080
