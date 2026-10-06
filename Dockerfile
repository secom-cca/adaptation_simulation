# syntax=docker/dockerfile:1

# --- Frontend build ---
FROM node:20-alpine AS frontend
WORKDIR /app/frontend-new
COPY frontend-new/package.json frontend-new/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY frontend-new/ ./
# Same-origin /api via nginx in the runtime image
ENV VITE_API_BASE=/api
RUN npm run build

# --- Runtime: nginx + FastAPI ---
FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY --from=frontend /app/frontend-new/dist /app/frontend-dist
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p /app/backend/data/operation_logs \
    && nginx -t

ENV UVICORN_WORKERS=2 \
    OLLAMA_HOST=http://127.0.0.1:11434 \
    LLM_MAX_CONCURRENCY=3 \
    PYTHONUNBUFFERED=1

EXPOSE 80
WORKDIR /app/backend
CMD ["/entrypoint.sh"]
