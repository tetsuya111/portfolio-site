# portfolio-importer が生成した Dockerfile。必要に応じて編集してください。
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# /data は DB を置く名前付きボリュームのマウント先。初回のマウントでイメージの所有者（appuser）が引き継がれる
RUN useradd --create-home appuser && mkdir /data && chown appuser:appuser /app /data
COPY --chown=appuser:appuser . .
RUN pip install --no-cache-dir .
# DB をボリューム（/data）に置く（.env の DB_PATH で上書きできる）
ENV DB_PATH=/data/app.db
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:create_default_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
