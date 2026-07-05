FROM apache/airflow:2.9.2-python3.11

USER airflow

# Create an isolated project directory so uv never reads Airflow's pyproject.toml
WORKDIR /opt/airflow/app

# Bring uv from its official distroless image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy your project metadata + lockfile
COPY --chown=airflow:root pyproject.toml uv.lock ./

# Create a venv that can still access Airflow's system packages
RUN uv venv --system-site-packages .venv && \
    uv sync --no-cache --project pyproject.toml

# Expose your synced deps to Airflow without touching PATH
ENV PYTHONPATH="/opt/airflow/app/.venv/lib/python3.11/site-packages:${PYTHONPATH}"

# Airflow expects /opt/airflow/dags to exist, so keep it untouched
WORKDIR /opt/airflow
