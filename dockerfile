FROM apache/airflow:2.9.2-python3.11

USER airflow
RUN pip install --no-cache-dir \
    openai \
    requests