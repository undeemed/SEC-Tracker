"""
Tests for api/middleware/rate_limit.py

Focus: ensure rate limiting identifiers can't be trivially bypassed.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from starlette.requests import Request


def _make_request(headers: dict[str, str] | None = None, client: tuple[str, int] = ("1.2.3.4", 12345)) -> Request:
    headers = headers or {}
    scope = {
        "type": "http",
        "asgi": {"spec_version": "2.3", "version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/v1/test",
        "raw_path": b"/api/v1/test",
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": client,
        "server": ("testserver", 80),
    }
    return Request(scope)


class FakeRedis:
    def __init__(self):
        self._zsets: dict[str, dict[str, int]] = {}
        self._expires: dict[str, int] = {}

    def pipeline(self):
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, redis: FakeRedis):
        self._redis = redis
        self._ops: list[tuple] = []

    def zremrangebyscore(self, key: str, min_score: int, max_score: int):
        self._ops.append(("zremrangebyscore", key, min_score, max_score))
        return self

    def zadd(self, key: str, mapping: dict[str, int]):
        self._ops.append(("zadd", key, mapping))
        return self

    def zcard(self, key: str):
        self._ops.append(("zcard", key))
        return self

    def zrange(self, key: str, start: int, end: int, withscores: bool = False):
        self._ops.append(("zrange", key, start, end, withscores))
        return self

    def expire(self, key: str, ttl_seconds: int):
        self._ops.append(("expire", key, ttl_seconds))
        return self

    async def execute(self):
        results = []
        for op in self._ops:
            name = op[0]
            if name == "zremrangebyscore":
                _, key, min_score, max_score = op
                zset = self._redis._zsets.get(key, {})
                to_delete = [m for m, s in zset.items() if min_score <= s <= max_score]
                for m in to_delete:
                    del zset[m]
                self._redis._zsets[key] = zset
                results.append(len(to_delete))
            elif name == "zadd":
                _, key, mapping = op
                zset = self._redis._zsets.get(key, {})
                added = 0
                for member, score in mapping.items():
                    if member not in zset:
                        added += 1
                    zset[member] = int(score)
                self._redis._zsets[key] = zset
                results.append(added)
            elif name == "zcard":
                _, key = op
                results.append(len(self._redis._zsets.get(key, {})))
            elif name == "zrange":
                _, key, start, end, withscores = op
                items = list(self._redis._zsets.get(key, {}).items())
                items.sort(key=lambda kv: (kv[1], kv[0]))
                selected = items[start : end + 1] if end >= 0 else items[start:]
                if withscores:
                    results.append([(member, float(score)) for member, score in selected])
                else:
                    results.append([member for member, _score in selected])
            elif name == "expire":
                _, key, ttl_seconds = op
                self._redis._expires[key] = int(ttl_seconds)
                results.append(True)
            else:
                raise AssertionError(f"Unhandled pipeline op: {name}")

        self._ops.clear()
        return results


@pytest.mark.asyncio
async def test_get_client_id_invalid_api_key_falls_back_to_ip(monkeypatch):
    from api.middleware.rate_limit import RateLimitMiddleware

    middleware = RateLimitMiddleware(app=MagicMock())

    async def fake_validate(_api_key: str):
        return None

    monkeypatch.setattr(middleware, "_validate_api_key", fake_validate)

    request = _make_request(headers={"X-API-Key": "not-a-real-key"})
    client_id = await middleware._get_client_id(request)

    assert client_id == "ip:1.2.3.4"


@pytest.mark.asyncio
async def test_get_client_id_valid_api_key_maps_to_user(monkeypatch):
    from api.middleware.rate_limit import RateLimitMiddleware

    middleware = RateLimitMiddleware(app=MagicMock())

    async def fake_validate(_api_key: str):
        return "user-123"

    monkeypatch.setattr(middleware, "_validate_api_key", fake_validate)

    request = _make_request(headers={"X-API-Key": "valid-key"})
    client_id = await middleware._get_client_id(request)

    assert client_id == "user:user-123"


@pytest.mark.asyncio
async def test_get_client_id_ignores_x_forwarded_for(monkeypatch):
    from api.middleware.rate_limit import RateLimitMiddleware

    middleware = RateLimitMiddleware(app=MagicMock())

    request = _make_request(headers={"X-Forwarded-For": "9.9.9.9"})
    client_id = await middleware._get_client_id(request)

    assert client_id == "ip:1.2.3.4"


@pytest.mark.asyncio
async def test_get_client_id_uses_x_forwarded_for_when_proxy_trusted(monkeypatch):
    from api.middleware.rate_limit import RateLimitMiddleware
    import ipaddress

    middleware = RateLimitMiddleware(app=MagicMock())
    middleware._trusted_proxy_networks = [ipaddress.ip_network("1.2.3.4/32")]

    request = _make_request(headers={"X-Forwarded-For": "9.9.9.9"}, client=("1.2.3.4", 12345))
    client_id = await middleware._get_client_id(request)

    assert client_id == "ip:9.9.9.9"


@pytest.mark.asyncio
async def test_check_rate_limit_denies_after_rpm(monkeypatch):
    import api.middleware.rate_limit as rate_limit_module
    from api.middleware.rate_limit import RateLimitMiddleware

    fake_redis = FakeRedis()
    monkeypatch.setattr(rate_limit_module, "get_redis_client", AsyncMock(return_value=fake_redis))

    # Deterministic time (increments by 1ms per call to avoid member collisions)
    times = iter([1000.001, 1000.002, 1000.003])
    monkeypatch.setattr(rate_limit_module.time, "time", lambda: next(times))

    middleware = RateLimitMiddleware(app=MagicMock(), requests_per_minute=2, requests_per_hour=1000)

    allowed, _ = await middleware._check_rate_limit("ip:1.2.3.4")
    assert allowed is True
    allowed, _ = await middleware._check_rate_limit("ip:1.2.3.4")
    assert allowed is True
    allowed, retry_after = await middleware._check_rate_limit("ip:1.2.3.4")
    assert allowed is False
    assert retry_after > 0
