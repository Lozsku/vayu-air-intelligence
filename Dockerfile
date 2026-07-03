# Vayu — portable container (runs on Cloud Run, any VM, or ARM/A1).
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 VAYU_PORT=8080

COPY requirements.txt .
# google-genai is optional; core deps are enough to run the local assistant.
RUN pip install --no-cache-dir Flask==3.0.3 flask-cors==4.0.1 requests==2.32.3 \
    python-dotenv==1.0.1 numpy==1.26.4 gunicorn==22.0.0

COPY . .

EXPOSE 8080
# Cloud Run injects $PORT; default to 8080. 2 workers, gthread for I/O concurrency.
CMD exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 60 app:app
