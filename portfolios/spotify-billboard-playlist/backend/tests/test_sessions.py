from app.sessions import SESSION_IDLE_TIMEOUT, SESSION_MAX_AGE, Session, SessionStore


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


def _clock(start=1000.0):
    now = [start]
    return now, (lambda: now[0])


def test_session_expires_after_max_age():
    now, clock = _clock()
    store = SessionStore(clock=clock)
    sid = store.create(Session("a", "r", 1.0, "u", "n"))
    step = SESSION_IDLE_TIMEOUT - 60
    while now[0] + step <= 1000.0 + SESSION_MAX_AGE:
        now[0] += step
        assert store.get(sid) is not None
    now[0] = 1000.0 + SESSION_MAX_AGE + 1
    assert store.get(sid) is None


def test_session_expires_after_idle():
    now, clock = _clock()
    store = SessionStore(clock=clock)
    sid = store.create(Session("a", "r", 1.0, "u", "n"))
    now[0] += SESSION_IDLE_TIMEOUT + 1
    assert store.get(sid) is None
    now[0] = 1000.0  # 時計を戻しても削除済みなので復活しない
    assert store.get(sid) is None


def test_session_access_extends_idle():
    now, clock = _clock()
    store = SessionStore(clock=clock)
    sid = store.create(Session("a", "r", 1.0, "u", "n"))
    for _ in range(3):
        now[0] += 23 * 3600
        assert store.get(sid) is not None


def test_oldest_session_evicted_at_capacity():
    now, clock = _clock()
    store = SessionStore(clock=clock, max_sessions=2)
    sids = []
    for _ in range(3):
        sids.append(store.create(Session("a", "r", 1.0, "u", "n")))
        now[0] += 1
    assert store.get(sids[0]) is None
    assert store.get(sids[1]) is not None
    assert store.get(sids[2]) is not None


def test_csrf_token_set_and_unique():
    store = SessionStore()
    s1 = Session("a", "r", 1.0, "u", "n")
    s2 = Session("a", "r", 1.0, "u", "n")
    store.create(s1)
    store.create(s2)
    assert len(s1.csrf_token) >= 32
    assert s1.csrf_token != s2.csrf_token
    assert s1.csrf_token not in repr(s1)
