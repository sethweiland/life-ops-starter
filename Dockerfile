# Production Dockerfile for the life-ops Flask shell
FROM python:3.14-slim

WORKDIR /app

RUN groupadd --gid 10001 lifeops && useradd --uid 10001 --gid lifeops --no-create-home lifeops

COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY src/ ./src/
COPY web/ ./web/
COPY config/tenant.example.yaml ./config/tenant.example.yaml
COPY wsgi.py .

RUN mkdir -p /app/data /app/instance && chown -R lifeops:lifeops /app/data /app/instance
USER 10001:10001

EXPOSE 8080

CMD ["sh", "-c", "exec gunicorn -b 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120 wsgi:app"]
