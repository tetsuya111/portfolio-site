"""バックエンドの Dockerfile・.dockerignore の生成と、docker によるイメージ作成。"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from importer import PortfolioError
from importer.detect import Backend, has_script, read_package_json
from importer.ignore import iter_files

PYTHON_PORT = 8000
NODE_PORT = 3000
_UVICORN = re.compile(r"uvicorn\s+([A-Za-z_][\w.]*:[A-Za-z_]\w*)(\s+--factory)?")
_FASTAPI_ASSIGN = re.compile(r"^([A-Za-z_]\w*)\s*=\s*FastAPI\(", re.MULTILINE)
_HAS_CMD = re.compile(r"^\s*(CMD|ENTRYPOINT)\b", re.MULTILINE | re.IGNORECASE)

DOCKERIGNORE = """\
.git
.env
.env.*
!.env.example
*.sqlite
*.sqlite3
*.db
.venv
venv
__pycache__
*.egg-info
.pytest_cache
.ruff_cache
node_modules
tests
*.pem
*.key
*.p12
*.pfx
*.jks
*.keystore
*.secret
id_rsa*
id_ed25519*
.npmrc
credentials*.json
service-account*.json
secrets.*
Dockerfile
.dockerignore
"""


@dataclass
class DockerResult:
    dockerfile: Path
    has_cmd: bool  # 起動コマンドがあり、イメージを作れる状態か
    warnings: list[str] = field(default_factory=list)


def _command_sources(d: Path):
    """起動コマンドを探すファイル（テストは .dockerignore でイメージから除くため対象外）を順に返す。"""
    for rel in iter_files(d):
        if rel.parts[0] in ("tests", "test") or rel.name.startswith("test_"):
            continue
        if rel.suffix == ".py" or rel.name.lower() == "readme.md":
            yield rel


def _python_command(d: Path) -> list[str] | None:
    host = ["--host", "0.0.0.0", "--port", str(PYTHON_PORT)]
    assign: list[str] | None = None
    for rel in _command_sources(d):
        text = (d / rel).read_text(encoding="utf-8", errors="replace")
        m = _UVICORN.search(text)
        if m:
            # 記載された起動方法を最優先する（見つかった時点で探索をやめる）
            return ["uvicorn", m.group(1)] + (["--factory"] if m.group(2) else []) + host
        if assign is None and rel.suffix == ".py":
            a = _FASTAPI_ASSIGN.search(text)
            if a:
                assign = ["uvicorn", f"{'.'.join(rel.with_suffix('').parts)}:{a.group(1)}"] + host
    if assign is not None:
        return assign
    if (d / "main.py").is_file():
        return ["python", "main.py"]
    return None


def _cmd_line(cmd: list[str] | None) -> str:
    if cmd is None:
        return ("# TODO: 起動コマンドを判定できませんでした。CMD を追記してからイメージを作成してください。\n"
                '# CMD ["..."]\n')
    return f"CMD {json.dumps(cmd, ensure_ascii=False)}\n"


def _env_lines(env: dict[str, str]) -> str:
    # 値は envvars で引用符などを含まない URL に限定済み
    return "".join(f"ENV {name}={json.dumps(env[name])}\n" for name in sorted(env))


def _python_dockerfile(d: Path, env: dict[str, str]) -> tuple[str, bool]:
    # 依存は requirements.txt を優先し、pyproject.toml は [project] があるときだけパッケージとして入れる
    # （ツール設定だけの pyproject.toml で pip install . すると依存が入らない・失敗するため）
    steps = []
    if (d / "requirements.txt").is_file():
        steps.append("pip install --no-cache-dir -r requirements.txt")
    pyproject = d / "pyproject.toml"
    if pyproject.is_file() and re.search(r"^\[project\]", pyproject.read_text(encoding="utf-8", errors="replace"),
                                         re.MULTILINE):
        steps.append("pip install --no-cache-dir .")
    install = " && ".join(steps) or "true"
    cmd = _python_command(d)
    text = (
        "# portfolio-importer が生成した Dockerfile。必要に応じて編集してください。\n"
        "FROM python:3.12-slim\n"
        "ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1\n"
        "WORKDIR /app\n"
        # 実行ユーザーがアプリのディレクトリ（SQLite などのデータ）に書き込めるよう、所有者を合わせる
        "RUN useradd --create-home appuser\n"
        "COPY --chown=appuser:appuser . .\n"
        f"RUN {install}\n"
        "USER appuser\n"
        + _env_lines(env)
        + f"EXPOSE {PYTHON_PORT}\n"
        + _cmd_line(cmd)
    )
    return text, cmd is not None


def _node_dockerfile(d: Path, env: dict[str, str]) -> tuple[str, bool]:
    pkg = read_package_json(d / "package.json") or {}
    build = has_script(pkg, "build")
    install = "npm ci" if (d / "package-lock.json").is_file() else "npm install"
    if not build:
        install += " --omit=dev"
    cmd = ["npm", "start"] if has_script(pkg, "start") else None
    text = (
        "# portfolio-importer が生成した Dockerfile。必要に応じて編集してください。\n"
        "FROM node:22-slim\n"
        "WORKDIR /app\n"
        # 実行ユーザー（node）がアプリのディレクトリに書き込めるよう、所有者を合わせてから依存を入れる
        "RUN chown node:node /app\n"
        "USER node\n"
        "COPY --chown=node:node package*.json ./\n"
        f"RUN {install}\n"
        "COPY --chown=node:node . .\n"
        # build スクリプトがあれば、開発用の依存を使ってビルドしてから取り除く
        + ("RUN npm run build && npm prune --omit=dev\n" if build else "")
        + "ENV NODE_ENV=production\n"
        + _env_lines(env)
        + f"EXPOSE {NODE_PORT}\n"
        + _cmd_line(cmd)
    )
    return text, cmd is not None


def write_docker_files(backend: Backend, env: dict[str, str] | None = None) -> DockerResult:
    """Dockerfile・.dockerignore を生成する。env（フロントエンドの URL など）は Dockerfile の ENV に書く。"""
    env = env or {}
    d = backend.dir
    dockerfile = d / "Dockerfile"
    warnings: list[str] = []
    if dockerfile.exists():
        warnings.append(f"{dockerfile.name} が既にあるため上書きしませんでした")
        existing = dockerfile.read_text(encoding="utf-8", errors="replace")
        lines = existing.splitlines()
        missing, differs = [], []
        for name in sorted(env):
            line = _env_lines({name: env[name]}).rstrip("\n")
            if line in lines:
                continue  # 前回の実行で生成した Dockerfile など、同じ行が既にある
            # 書き方が違う・古い値の ENV が既にあれば、追記ではなく直すよう案内する（重複すると後の行が勝つため）
            has_name = re.search(rf"^\s*ENV\s+{re.escape(name)}[\s=]", existing, re.MULTILINE | re.IGNORECASE)
            (differs if has_name else missing).append(line)
        if missing:
            warnings.append(f"{dockerfile.name} が既にあるため、次の行を手で追記してください: " + " / ".join(missing))
        if differs:
            warnings.append(f"{dockerfile.name} の ENV が生成する値と違います。必要なら既存の行を次のように直してください: "
                            + " / ".join(differs))
        has_cmd = bool(_HAS_CMD.search(existing))
    else:
        text, has_cmd = _python_dockerfile(d, env) if backend.kind == "python" else _node_dockerfile(d, env)
        dockerfile.write_text(text, encoding="utf-8", newline="\n")
    if not has_cmd:
        warnings.append("Dockerfile に起動コマンド（CMD）がないため、イメージを作成できません。CMD を追記してください")

    dockerignore = d / ".dockerignore"
    if dockerignore.exists():
        warnings.append(".dockerignore が既にあるため上書きしませんでした")
    else:
        dockerignore.write_text(DOCKERIGNORE, encoding="utf-8", newline="\n")
    return DockerResult(dockerfile, has_cmd, warnings)


def build_image(backend_dir: Path, slug: str, repo_root: Path, run=subprocess.run) -> Path:
    """docker build でイメージを作り、portfolios/docker-images/<スラッグ>-backend.tar に保存する。"""
    images = repo_root / "portfolios" / "docker-images"
    images.mkdir(parents=True, exist_ok=True)
    gitignore = images / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("# Docker イメージ（docker save の tar）は大きいため git で管理しない\n*.tar\n",
                             encoding="utf-8", newline="\n")
    tag = f"portfolio-{slug}-backend:latest"
    tar = images / f"{slug}-backend.tar"
    for args in (["docker", "build", "-t", tag, str(backend_dir)], ["docker", "save", "-o", str(tar), tag]):
        try:
            result = run(args, check=False)
        except FileNotFoundError as e:
            raise PortfolioError("docker コマンドが見つかりません。Docker をインストールしてください") from e
        if result.returncode != 0:
            raise PortfolioError(f"{' '.join(args[:2])} が失敗しました（終了コード {result.returncode}）")
    return tar
