# Project             :   Screenipy
# Author              :   Pranjal Joshi
# Created             :   17/08/2023
# Description         :   Dockerfile to build Screeni-py image for GUI release

FROM python:3.13-slim-bookworm AS base

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    git vim nano wget curl build-essential && \
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

WORKDIR /opt/program

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy project files for uv
COPY pyproject.toml uv.lock ./
COPY requirements.txt ./

# Create venv and install all deps via uv
# ta-lib >=0.6.5 ships pre-built manylinux wheels for amd64+arm64 on Python 3.9-3.13
# — no C compiler or system library build required
RUN uv venv /venv
ENV PATH=/venv/bin:$PATH
ENV UV_PROJECT_ENVIRONMENT=/venv

RUN uv pip install --python /venv/bin/python -r requirements.txt
RUN uv pip install --python /venv/bin/python --no-deps advanced-ta pandas-ta-remake

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
