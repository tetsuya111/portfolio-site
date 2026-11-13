from app.sessions import Session, SessionStore


def test_session_store_roundtrip():
    store = SessionStore()
    session = Session("a", "r", 1.0, "u1", "Tetsu")
    sid = store.create(session)
    assert len(sid) >= 40
    assert store.get(sid) is session
    store.delete(sid)
    assert store.get(sid) is None


def test_unknown_and_empty_sid():
    store = SessionStore()
    assert store.get("nope") is None
    assert store.get("") is None
    store.delete("nope")  # 例外にならない


def test_session_ids_are_unique():
    store = SessionStore()
    ids = {store.create(Session("a", "r", 1.0, "u", "n")) for _ in range(50)}
    assert len(ids) == 50


def test_session_repr_hides_tokens():
    text = repr(Session("secret-access", "secret-refresh", 1.0, "u1", "Tetsu"))
    assert "secret" not in text
