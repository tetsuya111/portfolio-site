"""プロジェクト内のフロントエンド・バックエンドの検出。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

FRONTEND_DIRS = ["frontend", "web", "client", "."]
BACKEND_DIRS = ["backend", "server", "api"]
NODE_BACKEND_DEPS = {"express": "Express", "fastify": "Fastify", "koa": "Koa", "@nestjs/core": "NestJS", "hono": "Hono"}
FRONTEND_TAG_DEPS = {"react": "React", "vue": "Vue", "svelte": "Svelte", "next": "Next.js", "astro": "Astro",
                     "vite": "Vite", "typescript": "TypeScript"}
PYTHON_TAG_DEPS = {"fastapi": "FastAPI", "flask": "Flask", "django": "Django"}
_NEXT_EXPORT = re.compile(r"""output\s*:\s*["']export["']""")


@dataclass
class Frontend:
    dir: Path
    kind: str | None  # vite / astro / next-export。S3 で配信できなければ None
    output_dir: str | None
    build_args: list[str] = field(default_factory=list)
    reason: str | None = None  # 配信できない理由
    tags: list[str] = field(default_factory=list)


@dataclass
class Backend:
    dir: Path
    kind: str  # python / node
    tags: list[str] = field(default_factory=list)


def read_package_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _deps(pkg: dict) -> dict:
    deps = {}
    for key in ("dependencies", "devDependencies"):
        value = pkg.get(key)
        if isinstance(value, dict):
            deps.update(value)
    return deps


def _has_script(pkg: dict, name: str) -> bool:
    scripts = pkg.get("scripts")
    return isinstance(scripts, dict) and isinstance(scripts.get(name), str)


def _tags(deps: dict, table: dict[str, str]) -> list[str]:
    return [tag for dep, tag in table.items() if dep in deps]


def detect_frontend(project: Path, slug: str) -> Frontend | None:
    base = f"/apps/{slug}/"
    for name in FRONTEND_DIRS:
        d = project if name == "." else project / name
        pkg = read_package_json(d / "package.json")
        if pkg is None or not _has_script(pkg, "build"):
            continue
        deps = _deps(pkg)
        tags = _tags(deps, FRONTEND_TAG_DEPS)
        if "next" in deps:
            configs = [p.read_text(encoding="utf-8", errors="replace") for p in d.glob("next.config.*") if p.is_file()]
            if any(_NEXT_EXPORT.search(c) for c in configs):
                return Frontend(d, "next-export", "out", [], None, tags)
            return Frontend(d, None, None, [], 'Next.js に output: "export" の設定がなく、静的ファイルを出力できません', tags)
        if "astro" in deps:
            return Frontend(d, "astro", "dist", ["--base", base], None, tags)
        if "vite" in deps:
            return Frontend(d, "vite", "dist", [f"--base={base}"], None, tags)
        if name == ".":
            # ルートの package.json は、フレームワークが判別できないときはフロントエンドとみなさない
            continue
        return Frontend(d, None, None, [], "静的出力に対応したフレームワーク（Vite・Astro・Next.js の静的出力）を判別できません", tags)
    return None


def _python_tags(d: Path) -> list[str]:
    text = ""
    for name in ("pyproject.toml", "requirements.txt"):
        p = d / name
        if p.is_file():
            text += p.read_text(encoding="utf-8", errors="replace").lower()
    return ["Python"] + [tag for dep, tag in PYTHON_TAG_DEPS.items() if re.search(rf"\b{dep}\b", text)]


def _is_python(d: Path) -> bool:
    return (d / "pyproject.toml").is_file() or (d / "requirements.txt").is_file()


def detect_backend(project: Path, frontend: Frontend | None) -> Backend | None:
    for name in BACKEND_DIRS:
        d = project / name
        if _is_python(d):
            return Backend(d, "python", _python_tags(d))
        pkg = read_package_json(d / "package.json")
        if pkg is not None:
            return Backend(d, "node", ["Node.js"] + _tags(_deps(pkg), NODE_BACKEND_DEPS))
    if _is_python(project):
        return Backend(project, "python", _python_tags(project))
    pkg = read_package_json(project / "package.json")
    if pkg is not None and not (frontend and frontend.dir == project):
        server_tags = _tags(_deps(pkg), NODE_BACKEND_DEPS)
        if server_tags:
            return Backend(project, "node", ["Node.js"] + server_tags)
    return None
