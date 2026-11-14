# backend

タスク百葉箱のAPI（Django REST Framework）。

セットアップ・コマンド・環境変数・アーキテクチャは [docs/backend.md](../docs/backend.md) を参照。

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env   # 値を設定する
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_agents
.\.venv\Scripts\python manage.py runserver
```
