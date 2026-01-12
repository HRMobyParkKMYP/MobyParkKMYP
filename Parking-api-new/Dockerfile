FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ /app/api/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && sed -i 's/\r$//' /entrypoint.sh

WORKDIR /app/api
ENV PYTHONPATH=/app

ENTRYPOINT ["/entrypoint.sh"]