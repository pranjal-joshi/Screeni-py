# Project             :   Screenipy
# Author              :   Pranjal Joshi
# Created             :   17/08/2023
# Description         :   Dockerfile to build Screeni-py image for GUI release

FROM python:3.11.6-slim-bookworm as base

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y software-properties-common

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    vim nano wget curl \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* 

ENV LANG C.UTF-8

ADD . /opt/program/

ENV PATH="/opt/program:${PATH}"

WORKDIR /opt/program

RUN chmod +x *

WORKDIR /opt/program/
RUN python3 -m pip install --upgrade pip

RUN pip3 install -r "requirements.txt"
RUN pip3 install --no-deps advanced-ta

ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE

ENV SCREENIPY_DOCKER = TRUE

ENV SCREENIPY_GUI = TRUE

EXPOSE 8000
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

WORKDIR /opt/program/src/
ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]