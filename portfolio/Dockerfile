FROM python:3.13-alpine
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ /app/
ENV DATA_DIR=/data PYTHONUNBUFFERED=1
EXPOSE 8099
CMD ["python", "server.py"]
