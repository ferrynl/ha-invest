FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 FEEDBACK_DATABASE=/data/relay.sqlite3
WORKDIR /app
COPY feedback_service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    groupadd --gid 10001 relay && useradd --uid 10001 --gid relay --no-create-home relay && \
    mkdir /data && chown relay:relay /data
COPY feedback_service/ /app/feedback_service/
USER 10001:10001
VOLUME ["/data"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).read()"
CMD ["python", "-m", "feedback_service", "serve"]
