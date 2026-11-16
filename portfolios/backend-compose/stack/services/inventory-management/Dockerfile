# 在庫管理システムのバックエンド（FastAPI）。
# DB（SQLite）は /data に置く想定（DATABASE_URL=sqlite:////data/inventory.db、/data をボリュームにマウント）。
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    DATABASE_URL=sqlite:////data/inventory.db

WORKDIR /app
RUN useradd --create-home appuser \
    && mkdir -p /data \
    && chown appuser:appuser /app /data

COPY pyproject.toml ./
COPY app ./app
RUN pip install .
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser alembic ./alembic

USER appuser
EXPOSE 8000

# 起動のたびにマイグレーションを適用してから API を起動する（適用済みなら何もしない）。
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers"]
