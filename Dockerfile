# Project             :   Screenipy
# Author              :   Pranjal Joshi
# Created             :   17/08/2023
# Description         :   Dockerfile to build Screeni-py image for GUI release

FROM python:3.11-slim-bookworm AS base

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

# Install TA-Lib system library from bundled source
COPY .github/dependencies/ta-lib-0.4.0-src.tar.gz /tmp/
RUN cd /tmp && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
    ./configure --prefix=/usr && \
    make && make install && \
    ldconfig && \
    cd / && rm -rf /tmp/ta-lib*

# Copy project files for uv
COPY pyproject.toml uv.lock ./
COPY requirements.txt ./

# Create venv and install all deps via uv
RUN uv venv /venv
ENV PATH=/venv/bin:$PATH
ENV UV_PROJECT_ENVIRONMENT=/venv

RUN uv pip install --python /venv/bin/python -r requirements.txt
RUN uv pip install --python /venv/bin/python --no-deps advanced-ta

##############
# Package Phase
##############
FROM base AS app

# Install TA-Lib runtime shared libraries
COPY --from=build /usr/lib/libta_lib* /usr/lib/
COPY --from=build /usr/include/ta-lib /usr/include/ta-lib
RUN ldconfig

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
