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
# 環境変数 INVENTORY_ADMIN_USERNAME・INVENTORY_ADMIN_PASSWORD（8文字以上）があれば、ログイン用の管理者も作る。
# 同様に INVENTORY_VISITOR_USERNAME・INVENTORY_VISITOR_PASSWORD（8文字以上）があれば、閲覧者（読み取り専用）も作る。
# 既に作成済みなら作成はエラーになるが、起動は続ける（|| true）。パスワードはイメージに含めず .env で渡すこと。
CMD ["sh", "-c", "alembic upgrade head && if [ -n \"$INVENTORY_ADMIN_USERNAME\" ] && [ -n \"$INVENTORY_ADMIN_PASSWORD\" ]; then python -m app.cli create-admin --username \"$INVENTORY_ADMIN_USERNAME\" || true; fi && if [ -n \"$INVENTORY_VISITOR_USERNAME\" ] && [ -n \"$INVENTORY_VISITOR_PASSWORD\" ]; then python -m app.cli create-visitor --username \"$INVENTORY_VISITOR_USERNAME\" || true; fi && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers"]
