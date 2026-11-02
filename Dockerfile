FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_URL=/
RUN env -u NITRO_PRESET npm run build

FROM python:3.12-slim AS runtime
RUN pip install --no-cache-dir uv==0.11.7
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    STATIC_DIR=/app/static
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev \
    && groupadd --gid 10001 gradematch \
    && useradd --uid 10001 --gid gradematch --no-create-home gradematch
COPY backend/app/ ./app/
COPY backend/alembic.ini ./
COPY backend/migrations/ ./migrations/
COPY --chmod=755 backend/start.sh ./start.sh
COPY --from=frontend /build/.output/public/ ./static/
USER 10001:10001
EXPOSE 8091
ENTRYPOINT ["/app/start.sh"]
