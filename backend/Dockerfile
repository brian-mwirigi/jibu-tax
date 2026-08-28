# File: backend/Dockerfile
# Description:
#   Docker Container Definition for JibuTax FastAPI Backend.
#   - Base: Python 3.10-slim.
#   - Installs PostgreSQL system client libraries.
#   - Installs requirements and runs Uvicorn on port 8000.

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
