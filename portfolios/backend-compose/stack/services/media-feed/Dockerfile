# backend-compose が生成した Dockerfile。必要に応じて編集してください。
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# /data は DB を置く名前付きボリュームのマウント先。初回のマウントでイメージの所有者（appuser）が引き継がれる
RUN useradd --create-home appuser && mkdir /data && chown appuser:appuser /app /data
COPY --chown=appuser:appuser . .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir gunicorn
# Django の既定の DB（/app/db.sqlite3）の実体をボリューム（/data）に置く（-wal・-shm もリンク先に作られる）
RUN ln -sf /data/db.sqlite3 /app/db.sqlite3
USER appuser
EXPOSE 8000
# 起動のたびにマイグレーションを適用する（空のボリュームでの初回の起動と、スキーマの更新のため）
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000"]
