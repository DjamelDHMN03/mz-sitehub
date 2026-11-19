"""
Limiteur de tentatives de connexion (section 82 : sécurité de l'authentification).

Audit Phase 21 : `/auth/login` n'avait aucune protection contre le
bourrage de mot de passe (brute force). Ce module ajoute une fenêtre
glissante en mémoire, simple et suffisante pour une V1 mono-instance (0 DA,
pas de Redis nécessaire — même limite assumée que le cache d'import Excel
en Phase 16).
"""
from __future__ import annotations

import time


class LoginRateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = {}

    def _prune(self, key: str, now: float) -> None:
        cutoff = now - self.window_seconds
        self._attempts[key] = [t for t in self._attempts.get(key, []) if t > cutoff]

    def is_blocked(self, key: str) -> bool:
        now = time.time()
        self._prune(key, now)
        return len(self._attempts.get(key, [])) >= self.max_attempts

    def record_failed_attempt(self, key: str) -> None:
        now = time.time()
        self._prune(key, now)
        self._attempts.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)

    def seconds_until_unblocked(self, key: str) -> int:
        attempts = self._attempts.get(key, [])
        if not attempts:
            return 0
        oldest_relevant = sorted(attempts)[0]
        remaining = self.window_seconds - (time.time() - oldest_relevant)
        return max(0, int(remaining))


login_rate_limiter = LoginRateLimiter()
