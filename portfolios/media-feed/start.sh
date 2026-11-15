#!/bin/bash
# バックエンドとフロントエンドを起動するスクリプト

echo "=== バックエンドセットアップ ==="
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

echo "=== フロントエンドセットアップ ==="
cd ../frontend
npm install
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "起動完了:"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo ""
echo "終了するには Ctrl+C を押してください"

wait
