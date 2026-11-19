from config.dotenv import load_env_file, parse_env


def test_parse_env():
    text = """
# コメント
GOOGLE_MAPS_GEOCODING_API_KEY=abc123
export ANTHROPIC_API_KEY = "sk-test"
QUOTED='a b'
EMPTY=
NOEQUAL
"""
    assert parse_env(text) == {
        "GOOGLE_MAPS_GEOCODING_API_KEY": "abc123",
        "ANTHROPIC_API_KEY": "sk-test",
        "QUOTED": "a b",
        "EMPTY": "",
    }


def test_load_env_file_does_not_override_existing(tmp_path):
    path = tmp_path / ".env"
    path.write_text("A=from-file\nB=from-file\n", encoding="utf-8")
    environ = {"A": "from-shell"}
    load_env_file(path, environ)
    assert environ == {"A": "from-shell", "B": "from-file"}


def test_missing_file_is_ignored(tmp_path):
    environ: dict[str, str] = {}
    load_env_file(tmp_path / "nothing.env", environ)
    assert environ == {}
