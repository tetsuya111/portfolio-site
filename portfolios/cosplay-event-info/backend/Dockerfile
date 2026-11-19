# コスプレイベント情報まとめサイトのバックエンド（Django REST Framework）。
# DB（SQLite）は /data に置く想定（DATABASE_PATH=/data/cosplay.db、/data をボリュームにマウント）。
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    DATABASE_PATH=/data/cosplay.db

WORKDIR /app
RUN useradd --create-home appuser \
    && mkdir -p /data \
    && chown appuser:appuser /app /data

COPY pyproject.toml ./
COPY config ./config
COPY catalog ./catalog
RUN pip install .
COPY --chown=appuser:appuser manage.py ./

USER appuser
EXPOSE 8000

# 起動のたびにマイグレーションを適用してから API を起動する（適用済みなら何もしない）。
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2"]
