FROM python:3.13-slim-bookworm
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "import duckdb; duckdb.connect().execute('INSTALL httpfs')"
COPY app/ /app/
ENV DATA_DIR=/data PYTHONUNBUFFERED=1
EXPOSE 8099 8100
CMD ["python", "server.py"]
