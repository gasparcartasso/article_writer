FROM apache/airflow:2.9.2-python3.11

USER airflow

WORKDIR /opt/airflow/app

COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /usr/local/bin/uv

COPY --chown=airflow:root pyproject.toml uv.lock ./

RUN uv venv --system-site-packages .venv && \
    uv sync --no-cache

ENV PYTHONPATH=""
ENV PYTHONPATH="/opt/airflow/app/.venv/lib/python3.11/site-packages:${PYTHONPATH}"

WORKDIR /opt/airflow

