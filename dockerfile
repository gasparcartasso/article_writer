#FROM apache/airflow:2.9.2-python3.11
#
#USER airflow
#RUN pip install --no-cache-dir \
#    openai \
#    requests \
#    dotenv

FROM apache/airflow:2.9.2-python3.11

USER airflow
WORKDIR /opt/airflow

# Grab the uv binary from its official distroless image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# uv sync needs both files -- uv.lock must be generated locally first
# with `uv lock` and committed alongside pyproject.toml
COPY --chown=airflow:root pyproject.toml uv.lock ./

# Create a venv that can still see Airflow's own installed packages
# (--system-site-packages), then install your locked deps into it
RUN uv venv --system-site-packages .venv && \
    uv sync --no-cache

# Expose the synced packages to the base image's Python/Airflow CLI
# without touching PATH (so `airflow ...` entrypoints keep working)
ENV PYTHONPATH="/opt/airflow/.venv/lib/python3.11/site-packages:${PYTHONPATH}"