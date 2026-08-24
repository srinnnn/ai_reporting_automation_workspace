FROM node:20.19-bookworm-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
COPY design-system /app/design-system
RUN npm run build

FROM python:3.12-slim AS runtime

ARG APP_COMMIT_SHA=local
ARG APP_BUILD_TIME=local
ARG APP_VERSION=3.0.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_ENV=production \
    INTRANET_HOST=0.0.0.0 \
    INTRANET_PORT=8785 \
    DATABASE_BACKEND=sqlite \
    RUNTIME_DIR=/app/runtime \
    APP_COMMIT_SHA=${APP_COMMIT_SHA} \
    APP_BUILD_TIME=${APP_BUILD_TIME} \
    APP_VERSION=${APP_VERSION}

WORKDIR /app

COPY requirements-prod.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements-prod.txt

COPY backend ./backend
COPY intranet_app ./intranet_app
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

RUN mkdir -p /app/runtime/uploads /app/runtime/results /app/runtime/logs

EXPOSE 8785

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8785/api/v1/health', timeout=3).read()"

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8785"]
