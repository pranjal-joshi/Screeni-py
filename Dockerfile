# Project             :   Screenipy
# Author              :   Pranjal Joshi
# Created             :   17/08/2023
# Description         :   Dockerfile to build Screeni-py image for GUI release

# FROM ubuntu:latest as base
# FROM tensorflow/tensorflow:2.9.2 as base
FROM python:3.9-slim as base

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

# Removed build ta-lib from source as we're using [pip3 install TA-Lib-Precompiled] for faster docker build

# WORKDIR /opt/program/.github/dependencies/
# RUN tar -xzf ta-lib-0.4.0-src.tar.gz

# WORKDIR /opt/program/.github/dependencies/ta-lib/
# RUN ./configure --prefix=/usr --build=$(uname -m)-unknown-linux-gnu
# RUN make
# RUN make install

WORKDIR /opt/program/
RUN python3 -m pip install --upgrade pip

RUN pip3 install -r "requirements.txt"

ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE

ENV SCREENIPY_DOCKER = TRUE

ENV SCREENIPY_GUI = TRUE

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

WORKDIR /opt/program/src/
ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]