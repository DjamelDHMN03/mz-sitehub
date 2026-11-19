"""
Tests du limiteur de connexion — bibliothèque standard uniquement.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.rate_limit import LoginRateLimiter


def test_not_blocked_initially():
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60)
    assert not limiter.is_blocked("test@example.com")


def test_blocked_after_max_attempts():
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60)
    for _ in range(3):
        limiter.record_failed_attempt("test@example.com")
    assert limiter.is_blocked("test@example.com")


def test_isolation_between_keys():
    limiter = LoginRateLimiter(max_attempts=1, window_seconds=60)
    limiter.record_failed_attempt("a@example.com")
    assert limiter.is_blocked("a@example.com")
    assert not limiter.is_blocked("b@example.com")


def test_reset_unblocks_immediately():
    limiter = LoginRateLimiter(max_attempts=1, window_seconds=60)
    limiter.record_failed_attempt("test@example.com")
    assert limiter.is_blocked("test@example.com")
    limiter.reset("test@example.com")
    assert not limiter.is_blocked("test@example.com")


def test_sliding_window_expires():
    limiter = LoginRateLimiter(max_attempts=1, window_seconds=1)
    limiter.record_failed_attempt("test@example.com")
    assert limiter.is_blocked("test@example.com")
    time.sleep(1.1)
    assert not limiter.is_blocked("test@example.com")


def test_seconds_until_unblocked_reasonable():
    limiter = LoginRateLimiter(max_attempts=1, window_seconds=60)
    limiter.record_failed_attempt("x")
    remaining = limiter.seconds_until_unblocked("x")
    assert 55 <= remaining <= 60
