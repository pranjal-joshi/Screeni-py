# Project             :   Screenipy
# Author              :   Pranjal Joshi
# Created             :   17/08/2023
# Description         :   Dockerfile to build Screeni-py image for release

# FROM ubuntu:latest as base
FROM tensorflow/tensorflow:2.9.2 as base

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y software-properties-common

RUN add-apt-repository ppa:deadsnakes/ppa

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.8 \
    python3-pip \
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

WORKDIR /opt/program/.github/dependencies/
RUN tar -xzf ta-lib-0.4.0-src.tar.gz

WORKDIR /opt/program/.github/dependencies/ta-lib/
RUN ./configure --prefix=/usr --build=x86_64-unknown-linux-gnu
RUN make
RUN make install

WORKDIR /opt/program/
RUN python3 -m pip install --upgrade pip
# RUN pip3 install ta-lib==0.4.24

RUN pip3 install -r "requirements.txt"

ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE

WORKDIR /opt/program/src/
# ENTRYPOINT [ "python3","screenipy.py" ]