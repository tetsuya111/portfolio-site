from app.ratelimit import RateLimiter


def _limiter(limit=3, window=60.0):
    now = [0.0]
    return now, RateLimiter(limit, window, clock=lambda: now[0])


def test_allows_up_to_limit_then_blocks():
    _, limiter = _limiter()
    assert [limiter.allow("a") for _ in range(4)] == [True, True, True, False]


def test_window_slides():
    now, limiter = _limiter()
    for _ in range(4):
        limiter.allow("a")
    now[0] += 61
    assert limiter.allow("a") is True


def test_keys_are_independent():
    _, limiter = _limiter()
    for _ in range(3):
        limiter.allow("a")
    assert limiter.allow("a") is False
    assert limiter.allow("b") is True


def test_stale_keys_are_swept_once_per_window():
    now, limiter = _limiter()
    for i in range(100):
        limiter.allow(f"k{i}")
    now[0] += 30
    limiter.allow("mid")  # ウィンドウ内なので全体の掃除はまだ行わない
    assert len(limiter._hits) == 101
    now[0] += 31
    limiter.allow("new")
    assert set(limiter._hits) == {"mid", "new"}
