"""
Batch Shell — バッチ管理・起動シェル

Usage:
  batch_shell [--list]

Options:
  --list    利用可能なバッチ一覧を表示して終了する

Shell 内コマンド:
  help                          利用可能なバッチ一覧と使い方を表示
  help <batch>                  指定バッチの引数ヘルプを表示
  run <batch> [args...] [--fg]  バッチを実行 (デフォルト: バックグラウンド)
  run list                      実行中のジョブ一覧を表示
  run kill <id>                 指定ジョブを強制終了
  exit / quit                   シェルを終了
"""
import importlib
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

COMMANDS_DIR = Path(__file__).parent
EXCLUDE = {"batch_shell"}
MANAGE_PY = str(Path(__file__).parents[4] / "manage.py")

# ── run コマンドの docopt usage ──────────────────────────
RUN_USAGE = """\
Usage:
  run list
  run kill <id>
  run <batch> [--fg] [<batch_args>...]

Options:
  --fg    フォアグラウンドで実行 (デフォルト: バックグラウンド)
"""

SHELL_USAGE = """\
=== Batch Shell コマンド一覧 ===

  help                          バッチ一覧と使い方を表示
  help <batch>                  指定バッチの引数ヘルプを表示
  run <batch> [args] [--fg]     バッチを実行 (デフォルト: バックグラウンド)
  run list                      実行中のジョブ一覧を表示
  run kill <id>                 指定ジョブを強制終了
  exit / quit                   シェルを終了

例:
  run get_dmm_images -k 素人          # バックグラウンド実行
  run get_dmm_images -k 素人 --fg     # フォアグラウンド実行
  run list                            # ジョブ一覧
  run kill 1                          # ジョブ ID=1 を強制終了
"""


# ────────────────────────────────────────────
# ユーティリティ
# ────────────────────────────────────────────

def _discover_batches() -> dict:
    batches = {}
    for path in sorted(COMMANDS_DIR.glob("*.py")):
        name = path.stem
        if name.startswith("_") or name in EXCLUDE:
            continue
        module_path = f"tools.management.commands.{name}"
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, "Command", None)
            if cls is not None:
                batches[name] = cls
        except Exception:
            pass
    return batches


def _batch_args_help(name: str, cls) -> str:
    instance = cls()
    lines = [f"[{name}]  {instance.help or '(説明なし)'}"]
    try:
        from io import StringIO
        from argparse import ArgumentParser
        parser = ArgumentParser(prog=f"run {name}", add_help=False)
        instance.add_arguments(parser)
        buf = StringIO()
        parser.print_help(buf)
        lines.append(buf.getvalue())
    except Exception:
        pass
    return "\n".join(lines)


def _print_batch_list(batches: dict, stdout) -> None:
    stdout.write("\n利用可能なバッチ:\n")
    for name, cls in batches.items():
        desc = cls().help or "(説明なし)"
        stdout.write(f"  {name:<35} {desc}\n")
    stdout.write("\n")


def _parse_run(tokens: list) -> dict | None:
    """
    run コマンドの引数を docopt で解析する。
    tokens は 'run' 以降のトークンリスト。
    """
    try:
        from docopt import docopt as _docopt, DocoptExit
    except ImportError:
        # docopt 未インストール時は手動パース
        return _parse_run_fallback(tokens)

    # --fg を一旦分離してから docopt に渡す
    fg = "--fg" in tokens
    clean = [t for t in tokens if t != "--fg"]

    try:
        args = _docopt(RUN_USAGE, argv=clean, options_first=True)
    except (SystemExit, Exception):
        return None

    return {
        "subcmd":      "list"  if args.get("list")
                       else "kill" if args.get("kill")
                       else "batch",
        "batch":       args.get("<batch>"),
        "batch_args":  args.get("<batch_args>", []),
        "kill_id":     args.get("<id>"),
        "fg":          fg,
    }


def _parse_run_fallback(tokens: list) -> dict | None:
    """docopt 非インストール時の簡易パーサ"""
    if not tokens:
        return None
    subcmd = tokens[0]
    if subcmd == "list":
        return {"subcmd": "list"}
    if subcmd == "kill":
        return {"subcmd": "kill", "kill_id": tokens[1] if len(tokens) > 1 else None, "batch": None, "batch_args": [], "fg": False}
    fg = "--fg" in tokens
    batch_args = [t for t in tokens[1:] if t != "--fg"]
    return {"subcmd": "batch", "batch": subcmd, "batch_args": batch_args, "fg": fg, "kill_id": None}


# ────────────────────────────────────────────
# ジョブ管理
# ────────────────────────────────────────────

class JobManager:
    def __init__(self):
        self._jobs: dict[int, dict] = {}
        self._next_id = 1

    def add(self, name: str, args: list, proc: subprocess.Popen) -> int:
        job_id = self._next_id
        self._next_id += 1
        self._jobs[job_id] = {
            "id":      job_id,
            "name":    name,
            "args":    args,
            "process": proc,
            "started": datetime.now().strftime("%H:%M:%S"),
        }
        return job_id

    def _cleanup(self):
        finished = [jid for jid, j in self._jobs.items() if j["process"].poll() is not None]
        for jid in finished:
            del self._jobs[jid]

    def list_jobs(self, stdout) -> None:
        self._cleanup()
        if not self._jobs:
            stdout.write("  実行中のジョブはありません\n")
            return
        stdout.write(f"  {'ID':<5} {'開始時刻':<10} {'バッチ名':<30} 引数\n")
        stdout.write("  " + "-" * 65 + "\n")
        for j in self._jobs.values():
            args_str = " ".join(j["args"])
            stdout.write(f"  {j['id']:<5} {j['started']:<10} {j['name']:<30} {args_str}\n")

    def kill(self, job_id_str: str, stdout, stderr) -> None:
        self._cleanup()
        try:
            jid = int(job_id_str)
        except (ValueError, TypeError):
            stderr.write(f"無効なジョブID: {job_id_str}\n")
            return
        if jid not in self._jobs:
            stderr.write(f"ジョブが見つかりません: {jid}\n")
            return
        j = self._jobs.pop(jid)
        j["process"].kill()
        stdout.write(f"ジョブ {jid} ({j['name']}) を強制終了しました\n")


# ────────────────────────────────────────────
# Django 管理コマンド
# ────────────────────────────────────────────

class Command(BaseCommand):
    help = "バッチを管理・起動するインタラクティブシェル"

    def add_arguments(self, parser):
        parser.add_argument("--list", action="store_true", help="バッチ一覧を表示して終了")

    def handle(self, *args, **options):
        batches = _discover_batches()
        jobs = JobManager()

        if options.get("list"):
            _print_batch_list(batches, self.stdout)
            return

        self.stdout.write("\n=== Batch Shell ===  (help で使い方 / exit で終了)\n")

        # タブ補完（readline がある環境）
        try:
            import readline
            candidates = list(batches.keys()) + ["run", "help", "exit", "quit"]
            readline.set_completer(
                lambda text, state: [c for c in candidates if c.startswith(text)][state]
                if state < len([c for c in candidates if c.startswith(text)]) else None
            )
            readline.parse_and_bind("tab: complete")
        except ImportError:
            pass

        while True:
            try:
                raw = input("batch> ").strip()
            except (EOFError, KeyboardInterrupt):
                self.stdout.write("\n終了します\n")
                break

            if not raw:
                continue

            try:
                tokens = shlex.split(raw)
            except ValueError as e:
                self.stderr.write(f"解析エラー: {e}\n")
                continue

            cmd = tokens[0].lower()

            # ── exit ──────────────────────────────────
            if cmd in ("exit", "quit","q"):
                self.stdout.write("終了します\n")
                break

            # ── help ──────────────────────────────────
            elif cmd == "help":
                if len(tokens) >= 2:
                    target = tokens[1]
                    if target in batches:
                        self.stdout.write(_batch_args_help(target, batches[target]) + "\n")
                    else:
                        self.stderr.write(f"バッチが見つかりません: {target}\n")
                else:
                    self.stdout.write(SHELL_USAGE)
                    _print_batch_list(batches, self.stdout)

            # ── run ───────────────────────────────────
            elif cmd == "run":
                parsed = _parse_run(tokens[1:])
                if parsed is None:
                    self.stdout.write(RUN_USAGE)
                    continue

                subcmd = parsed["subcmd"]

                if subcmd == "list":
                    jobs.list_jobs(self.stdout)

                elif subcmd == "kill":
                    jobs.kill(parsed["kill_id"], self.stdout, self.stderr)

                elif subcmd == "batch":
                    batch_name = parsed["batch"]
                    batch_args = parsed["batch_args"]
                    fg = parsed["fg"]

                    if batch_name not in batches:
                        self.stderr.write(f"バッチが見つかりません: {batch_name}\n")
                        continue

                    if fg:
                        # フォアグラウンド: call_command で直接実行
                        self.stdout.write(f"[FG] {batch_name} {' '.join(batch_args)}\n")
                        try:
                            call_command(batch_name, *batch_args,
                                         stdout=self.stdout, stderr=self.stderr)
                        except SystemExit:
                            pass
                        except Exception as e:
                            self.stderr.write(f"エラー: {e}\n")
                    else:
                        # バックグラウンド: subprocess.Popen で起動
                        cmd_args = [sys.executable, MANAGE_PY, batch_name] + batch_args
                        try:
                            proc = subprocess.Popen(
                                cmd_args,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            jid = jobs.add(batch_name, batch_args, proc)
                            self.stdout.write(
                                f"[BG] ジョブ {jid} 起動: {batch_name} {' '.join(batch_args)}"
                                f"  (PID {proc.pid})\n"
                            )
                        except Exception as e:
                            self.stderr.write(f"起動エラー: {e}\n")
                else:
                    self.stdout.write(RUN_USAGE)

            # ── 不明コマンド ───────────────────────────
            else:
                self.stderr.write(f"不明なコマンド: {cmd}  (help で一覧表示)\n")
