"""バックエンドのルート定義の検出と、フロントエンドのモック（apps/<スラッグ>/mock/handlers.js）の雛形の生成。

モックは portfolio-site の npm run build:apps が出力の HTML に差し込み、ブラウザで fetch を横取りして応答する
（バックエンドを常駐させずに S3 だけで動かすため）。応答の中身はスキル（Claude）が書く。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from importer.detect import Backend
from importer.ignore import iter_files

MOCK_HANDLERS = Path("mock") / "handlers.js"
_METHODS = "get|post|put|patch|delete"
# FastAPI など: @app.get("/x") / @router.post(\n "/x", ...)
_PY_METHOD = re.compile(rf"""@\w+(?:\.\w+)*\.({_METHODS})\(\s*["']([^"']+)["']""")
# Flask: @app.route("/x", methods=["GET", "POST"])
_PY_ROUTE = re.compile(r"""@\w+(?:\.\w+)*\.route\(\s*["']([^"']+)["']([^)]*)\)""")
_PY_ROUTE_METHODS = re.compile(r"""methods\s*=\s*[\[(]([^\])]*)[\])]""")
# Express・Fastify・Hono など: app.get("/x", ...) / router.post(`/x`, ...)
_NODE_METHOD = re.compile(rf"""\b\w+\.({_METHODS})\(\s*(["'`])(/[^"'`]*)\2""")
_NODE_SUFFIXES = {".js", ".mjs", ".cjs", ".ts", ".mts", ".cts"}
# パスの引数: {name} / {name:path} / <name> / <int:name>
_PARAM = re.compile(r"\{(\w+)(?::[^}]*)?\}|<(?:\w+:)?(\w+)>")


@dataclass(frozen=True)
class Route:
    method: str
    path: str


def _is_test(rel: Path) -> bool:
    name = rel.name
    return (any(p in ("tests", "test", "__tests__") for p in rel.parts[:-1]) or name.startswith("test_")
            or ".test." in name or ".spec." in name)


def _normalize(path: str) -> str:
    return _PARAM.sub(lambda m: ":" + (m.group(1) or m.group(2)), path)


def _python_routes(text: str) -> list[tuple[int, Route]]:
    found = [(m.start(), Route(m.group(1).upper(), _normalize(m.group(2)))) for m in _PY_METHOD.finditer(text)]
    for m in _PY_ROUTE.finditer(text):
        methods_m = _PY_ROUTE_METHODS.search(m.group(2))
        methods = re.findall(r"""["'](\w+)["']""", methods_m.group(1)) if methods_m else ["GET"]
        found += [(m.start(), Route(x.upper(), _normalize(m.group(1)))) for x in methods]
    return found


def _node_routes(text: str) -> list[tuple[int, Route]]:
    return [(m.start(), Route(m.group(1).upper(), _normalize(m.group(3)))) for m in _NODE_METHOD.finditer(text)]


def extract_routes(backend: Backend) -> list[Route]:
    """バックエンドのソース（テストを除く）から、ルートのメソッドとパスを見つけた順に返す（重複は除く）。"""
    routes: list[Route] = []
    for rel in iter_files(backend.dir):
        if _is_test(rel):
            continue
        if backend.kind == "python" and rel.suffix == ".py":
            parse = _python_routes
        elif backend.kind == "node" and rel.suffix in _NODE_SUFFIXES:
            parse = _node_routes
        else:
            continue
        text = (backend.dir / rel).read_text(encoding="utf-8", errors="replace")
        for _, route in sorted(parse(text), key=lambda x: x[0]):
            if route not in routes:
                routes.append(route)
    return routes


_HEADER = """\
// バックエンドのモック。portfolio-site の npm run build:apps が出力の HTML に差し込み、ブラウザで fetch を
// 横取りして応答する（バックエンドなしで S3 だけで動かすため）。portfolio-importer が雛形を作成した。
//
// portfolioMock.handle(メソッド, パス, (req) => 応答) で登録する。
// - パスの「:名前」は任意の1区間に一致し、req.params.名前 に入る。
// - req = { method, path, params, query（URLSearchParams）, body（JSON なら変換済み） }
// - 戻り値: オブジェクトなど → 200 の JSON / undefined・null → 204 / new Response(...) → そのまま。async も可。
// - このファイルは公開されるため、秘密情報を書かないこと。
"""

_EXAMPLE = """\
// ルートを検出できなかったため、フロントエンドが呼ぶ API に合わせて書き足すこと。例:
// portfolioMock.handle("GET", "/api/items/:id", (req) => {
//   return { id: req.params.id, name: "サンプル" };
// });
"""


def _handler(route: Route) -> str:
    return (f"\nportfolioMock.handle({json.dumps(route.method)}, {json.dumps(route.path)}, (req) => {{\n"
            "  // TODO: バックエンドの実装に合わせた応答を返す\n"
            "  return {};\n"
            "});\n")


def write_mock_handlers(app_dir: Path, routes: list[Route]) -> tuple[Path, list[str]]:
    """app_dir/mock/handlers.js に雛形を書く（既にあれば書かない）。パスと警告を返す。"""
    path = app_dir / MOCK_HANDLERS
    if path.exists():
        return path, [f"{MOCK_HANDLERS.as_posix()} が既にあるため上書きしませんでした"]
    warnings: list[str] = []
    if routes:
        body = "".join(_handler(r) for r in routes)
    else:
        body = "\n" + _EXAMPLE
        warnings.append("バックエンドのルートを検出できなかったため、モックのハンドラーを書き足してください")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_HEADER + body, encoding="utf-8", newline="\n")
    return path, warnings
