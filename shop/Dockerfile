# One image for every mini-shop service; the SERVICE env var selects which app runs.
# Build context must be the repo root:  docker build -f shop/Dockerfile .
FROM python:3.12-slim

WORKDIR /app
COPY shop/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shop ./shop

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    SERVICE=frontend

EXPOSE 8000
# Shell form so ${SERVICE} expands at runtime.
CMD ["sh", "-c", "uvicorn shop.${SERVICE}.main:app --host 0.0.0.0 --port 8000"]
