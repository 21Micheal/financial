# syntax=docker/dockerfile:1
# Multi-stage build for the financial-system Django app

# ── Stage 1: build Python deps ────────────────────────────────────────────────
FROM python:3.10-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    DEBIAN_FRONTEND=noninteractive

# Compile-time dependencies for both PostgreSQL and MySQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Runtime-only system packages for both PostgreSQL and MySQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmariadb3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV=/opt/venv

# Verify native lib linkage for both databases
RUN python -c "import psycopg2; print('native lib linkage OK (postgres)')"
RUN python -c "import MySQLdb; print('native lib linkage OK (mysql)')"

COPY . .

EXPOSE 8001

CMD ["gunicorn", "financial_system.wsgi:application", "--bind", "0.0.0.0:8001"]
