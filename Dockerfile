# Project             :   Screenipy
# Author              :   Pranjal Joshi
# Created             :   17/08/2023
# Description         :   Dockerfile to build Screeni-py image for GUI release

FROM python:3.11.6-slim-bookworm AS base

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    git vim nano wget curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* 

ENV LANG=C.UTF-8 \
    PYTHONUNBUFFERED=TRUE \
    PYTHONDONTWRITEBYTECODE=TRUE \
    SCREENIPY_DOCKER=TRUE \
    SCREENIPY_GUI=TRUE \
    PATH=/opt/program:$PATH

##############
# Build Phase
##############
FROM base AS build

ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ARG PIP_NO_CACHE_DIR=1

WORKDIR /opt/program

RUN python3 -m venv /venv
ENV PATH=/venv/bin:$PATH

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip pip3 install -r requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip3 install --no-deps advanced-ta

##############
# Package Phase
##############
FROM base AS app

COPY --from=build /venv /venv
ENV PATH=/venv/bin:$PATH

WORKDIR /opt/program

COPY . .

RUN chmod +x ./*

EXPOSE 8000

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

WORKDIR /opt/program/src

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
# ENTRYPOINT ["tail", "-f", "/dev/null"]
