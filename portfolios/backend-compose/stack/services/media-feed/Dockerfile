# backend-compose が生成した Dockerfile。必要に応じて編集してください。
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN useradd --create-home appuser
COPY --chown=appuser:appuser . .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir gunicorn
USER appuser
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
