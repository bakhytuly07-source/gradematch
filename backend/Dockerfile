FROM python:3.12.13-slim-bookworm

RUN pip install --no-cache-dir uv==0.11.7
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev \
    && groupadd --gid 10001 gradematch \
    && useradd --uid 10001 --gid gradematch --no-create-home gradematch
COPY app/ ./app/
COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY --chmod=755 start.sh ./start.sh
USER 10001:10001
EXPOSE 8091
ENTRYPOINT ["/app/start.sh"]
