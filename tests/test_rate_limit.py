from app.core.rate_limit import InMemoryRateLimiter


def test_rate_limiter_blocks_after_limit_then_expires():
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("127.0.0.1", now=0)
    assert limiter.allow("127.0.0.1", now=1)
    assert not limiter.allow("127.0.0.1", now=2)
    assert limiter.allow("127.0.0.1", now=60)
