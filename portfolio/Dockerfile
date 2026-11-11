FROM python:3.13-slim-bookworm
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "import duckdb; duckdb.connect().execute('INSTALL httpfs')"
COPY app/ /app/
ENV DATA_DIR=/data PYTHONUNBUFFERED=1
# Build tooling is not required at runtime; remove vendored libraries and bootstrap wheels.
RUN python -m pip check && \
    python -m pip uninstall -y pip && \
    python -c "import pathlib, sysconfig, shutil; shutil.rmtree(pathlib.Path(sysconfig.get_path('stdlib')) / 'ensurepip', ignore_errors=True)"
EXPOSE 8099 8100
CMD ["python", "server.py"]
