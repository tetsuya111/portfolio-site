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


def test_least_recently_used_session_evicted_at_capacity():
    now, clock = _clock()
    store = SessionStore(clock=clock, max_sessions=2)
    first = store.create(Session("a", "r", 1.0, "u1", "n"))
    now[0] += 1
    second = store.create(Session("a", "r", 1.0, "u2", "n"))
    now[0] += 1
    assert store.get(first) is not None  # first を使うと second の方が古くなる
    now[0] += 1
    third = store.create(Session("a", "r", 1.0, "u3", "n"))
    assert store.get(second) is None
    assert store.get(first) is not None
    assert store.get(third) is not None


def test_one_user_cannot_evict_other_users():
    now, clock = _clock()
    store = SessionStore(clock=clock, max_sessions=4, max_per_user=2)
    victim = store.create(Session("a", "r", 1.0, "victim", "n"))
    attacker = []
    for _ in range(10):
        now[0] += 1
        attacker.append(store.create(Session("a", "r", 1.0, "attacker", "n")))
    assert store.get(victim) is not None
    assert [store.get(sid) is not None for sid in attacker[-3:]] == [False, True, True]


def test_csrf_token_set_and_unique():
    store = SessionStore()
    s1 = Session("a", "r", 1.0, "u", "n")
    s2 = Session("a", "r", 1.0, "u", "n")
    store.create(s1)
    store.create(s2)
    assert len(s1.csrf_token) >= 32
    assert s1.csrf_token != s2.csrf_token
    assert s1.csrf_token not in repr(s1)
