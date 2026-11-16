"""バックエンドの Dockerfile・.dockerignore の生成と、待ち受けポートの判定。

生成の規則は、以前 portfolio-importer にあった処理（コミット ebf53fa）を元にしている。イメージは作らない
（VPS で docker compose が build する）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from importer.detect import has_script, read_package_json
from importer.ignore import iter_files

PYTHON_PORT = 8000
NODE_PORT = 3000
_UVICORN = re.compile(r"uvicorn\s+([A-Za-z_][\w.]*:[A-Za-z_]\w*)(\s+--factory)?")
_FASTAPI_ASSIGN = re.compile(r"^([A-Za-z_]\w*)\s*=\s*FastAPI\(", re.MULTILINE)
_FLASK_ASSIGN = re.compile(r"^([A-Za-z_]\w*)\s*=\s*Flask\(", re.MULTILINE)
_HAS_CMD = re.compile(r"^\s*(CMD|ENTRYPOINT)\b", re.MULTILINE | re.IGNORECASE)
_EXPOSE = re.compile(r"^\s*EXPOSE\s+(\d+)", re.MULTILINE | re.IGNORECASE)

# Docker の .dockerignore は、**/ を付けないとビルドコンテキストの直下にしか一致しない。秘密情報・依存・キャッシュは
# どの階層でも除く。secrets.* は設定ファイル形式だけにする（secrets.py などのソースは残す。importer のコピー規則と同じ）
DOCKERIGNORE = """\
**/.git
**/.env
**/.env.*
!**/.env.example
**/*.sqlite
**/*.sqlite3
**/*.db
**/.venv
**/venv
**/__pycache__
**/*.egg-info
**/.pytest_cache
**/.ruff_cache
**/node_modules
tests
**/*.pem
**/*.key
**/*.p12
**/*.pfx
**/*.jks
**/*.keystore
**/*.secret
**/id_rsa*
**/id_ed25519*
**/.npmrc
**/credentials*.json
**/service-account*.json
**/secrets.json
**/secrets.yaml
**/secrets.yml
**/secrets.toml
**/secrets.ini
**/secrets.env
**/secrets.txt
Dockerfile
.dockerignore
"""

_HEADER = "# backend-compose が生成した Dockerfile。必要に応じて編集してください。\n"


def _sources(d: Path):
    """起動コマンドを探すファイル（テストは .dockerignore でイメージから除くため対象外）を順に返す。"""
    for rel in sorted(iter_files(d)):
        if rel.parts[0] in ("tests", "test") or rel.name.startswith("test_"):
            continue
        if rel.suffix == ".py" or rel.name.lower() == "readme.md":
            yield rel


def _module(rel: Path) -> str:
    return ".".join(rel.with_suffix("").parts)


def _python_command(d: Path) -> tuple[list[str] | None, bool]:
    """起動コマンドと、gunicorn を入れる必要があるかを返す。"""
    host = ["--host", "0.0.0.0", "--port", str(PYTHON_PORT)]
    bind = ["--bind", f"0.0.0.0:{PYTHON_PORT}"]
    fastapi = wsgi = flask = None
    for rel in _sources(d):
        text = (d / rel).read_text(encoding="utf-8", errors="replace")
        m = _UVICORN.search(text)
        if m:
            # 記載された起動方法を最優先する（見つかった時点で探索をやめる）
            return ["uvicorn", m.group(1)] + (["--factory"] if m.group(2) else []) + host, False
        if rel.suffix != ".py":
            continue
        if fastapi is None and (a := _FASTAPI_ASSIGN.search(text)):
            fastapi = ["uvicorn", f"{_module(rel)}:{a.group(1)}"] + host
        if wsgi is None and rel.name == "wsgi.py" and (d / "manage.py").is_file():
            wsgi = ["gunicorn", f"{_module(rel)}:application"] + bind
        if flask is None and (a := _FLASK_ASSIGN.search(text)):
            flask = ["gunicorn", f"{_module(rel)}:{a.group(1)}"] + bind
    for cmd in (fastapi, wsgi, flask):
        if cmd is not None:
            return cmd, cmd[0] == "gunicorn"
    if (d / "main.py").is_file():
        return ["python", "main.py"], False
    return None, False


def _cmd_line(cmd: list[str] | None) -> str:
    if cmd is None:
        return ("# TODO: 起動コマンドを判定できませんでした。CMD を追記してから docker compose を実行してください。\n"
                '# CMD ["..."]\n')
    return f"CMD {json.dumps(cmd, ensure_ascii=False)}\n"


def _python_dockerfile(d: Path) -> tuple[str, bool]:
    # 依存は requirements.txt を優先し、pyproject.toml は [project] があるときだけパッケージとして入れる
    steps = []
    if (d / "requirements.txt").is_file():
        steps.append("pip install --no-cache-dir -r requirements.txt")
    pyproject = d / "pyproject.toml"
    if pyproject.is_file() and re.search(r"^\[project\]", pyproject.read_text(encoding="utf-8", errors="replace"),
                                         re.MULTILINE):
        steps.append("pip install --no-cache-dir .")
    cmd, gunicorn = _python_command(d)
    # 起動に使うサーバーは依存に書かれていないことがあるため入れる（既に入っていれば何もしない）
    if gunicorn:
        steps.append("pip install --no-cache-dir gunicorn")
    elif cmd is not None and cmd[0] == "uvicorn":
        steps.append("pip install --no-cache-dir uvicorn")
    install = " && ".join(steps) or "true"
    text = (
        _HEADER
        + "FROM python:3.12-slim\n"
        "ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1\n"
        "WORKDIR /app\n"
        # 実行ユーザーがアプリのディレクトリ（SQLite などのデータ）に書き込めるよう、所有者を合わせる
        "RUN useradd --create-home appuser\n"
        "COPY --chown=appuser:appuser . .\n"
        f"RUN {install}\n"
        "USER appuser\n"
        f"EXPOSE {PYTHON_PORT}\n"
        + _cmd_line(cmd)
    )
    return text, cmd is not None


def _node_dockerfile(d: Path) -> tuple[str, bool]:
    pkg = read_package_json(d / "package.json") or {}
    build = has_script(pkg, "build")
    install = "npm ci" if (d / "package-lock.json").is_file() else "npm install"
    if not build:
        install += " --omit=dev"
    cmd = ["npm", "start"] if has_script(pkg, "start") else None
    text = (
        _HEADER
        + "FROM node:22-slim\n"
        "WORKDIR /app\n"
        # 実行ユーザー（node）がアプリのディレクトリに書き込めるよう、所有者を合わせてから依存を入れる
        "RUN chown node:node /app\n"
        "USER node\n"
        "COPY --chown=node:node package*.json ./\n"
        f"RUN {install}\n"
        "COPY --chown=node:node . .\n"
        + ("RUN npm run build && npm prune --omit=dev\n" if build else "")
        + f"ENV NODE_ENV=production PORT={NODE_PORT}\n"
        f"EXPOSE {NODE_PORT}\n"
        + _cmd_line(cmd)
    )
    return text, cmd is not None


def write_docker_files(d: Path, kind: str) -> tuple[Path, list[str]]:
    """d（compose に置いたバックエンド）に Dockerfile・.dockerignore を書き、Dockerfile のパスと警告を返す。"""
    dockerfile = d / "Dockerfile"
    warnings: list[str] = []
    if dockerfile.exists():
        warnings.append(f"{dockerfile.name} が既にあるため上書きしませんでした")
        has_cmd = bool(_HAS_CMD.search(dockerfile.read_text(encoding="utf-8", errors="replace")))
    else:
        text, has_cmd = _python_dockerfile(d) if kind == "python" else _node_dockerfile(d)
        dockerfile.write_text(text, encoding="utf-8", newline="\n")
    if not has_cmd:
        warnings.append("Dockerfile に起動コマンド（CMD）がありません。CMD を追記してから docker compose を実行してください")
    dockerignore = d / ".dockerignore"
    if dockerignore.exists():
        warnings.append(".dockerignore が既にあるため上書きしませんでした")
    else:
        dockerignore.write_text(DOCKERIGNORE, encoding="utf-8", newline="\n")
    return dockerfile, warnings


def detect_port(text: str, kind: str) -> int:
    """Dockerfile の最初の EXPOSE のポート（なければ言語の既定値）。"""
    m = _EXPOSE.search(text)
    if m:
        return int(m.group(1))
    return PYTHON_PORT if kind == "python" else NODE_PORT
