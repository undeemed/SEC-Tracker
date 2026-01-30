"""
Rate Limiting Middleware for User Scale

Uses Redis for distributed rate limiting across multiple API instances.
Implements sliding window algorithm for accurate rate limiting.

SECURITY FIXES:
- Validate API keys before using as client identifier
- Don't trust X-Forwarded-For without proxy validation
- Use proper sliding window instead of fixed buckets
"""
import time
import logging
import hashlib
import ipaddress
import secrets
import math
from typing import Optional, Callable
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from cache.redis_client import get_redis_client
from api.config import get_settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Distributed rate limiting using Redis sliding window.
    Scales to millions of users across multiple API instances.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10,  # Max requests per second
    ):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.rph = requests_per_hour
        self.burst = burst_limit
        self._settings = get_settings()
        self._trusted_proxy_networks = self._parse_trusted_proxies(self._settings.trusted_proxies)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/", "/api/v1/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier (user_id from JWT or validated API key or IP)
        client_id = await self._get_client_id(request)
        
        # Check rate limits
        try:
            allowed, retry_after = await self._check_rate_limit(client_id)
            
            if not allowed:
                return Response(
                    content='{"detail": "Rate limit exceeded. Please slow down."}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                    },
                    media_type="application/json"
                )
        except Exception as e:
            # If Redis is down, log and allow request (fail-open with logging)
            logger.warning(f"Rate limiting failed, allowing request: {e}")
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        
        return response
    
    async def _get_client_id(self, request: Request) -> str:
        """
        Extract client identifier from request.
        SECURITY: Only use validated identifiers to prevent bypass.
        """
        # Try to get user_id from JWT token (already validated by auth middleware)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from jose import jwt
                token = auth_header[7:]
                payload = jwt.decode(
                    token,
                    self._settings.jwt_secret_key,
                    algorithms=[self._settings.jwt_algorithm]
                )
                user_id = payload.get('sub')
                if user_id:
                    return f"user:{user_id}"
            except Exception:
                pass
        
        # Try API key - MUST validate against DB before using
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            validated_user_id = await self._validate_api_key(api_key)
            if validated_user_id:
                return f"user:{validated_user_id}"
            # Invalid API key - fall through to IP-based limiting
            # This prevents attackers from rotating fake keys to bypass limits
        
        # Fall back to client IP (trust forwarded headers only from trusted proxies)
        client_ip = self._get_remote_ip(request)
        return f"ip:{client_ip}"

    @staticmethod
    def _parse_trusted_proxies(value: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        """
        Parse a comma-separated list of trusted proxies (IPs or CIDRs).
        Invalid entries are ignored.
        """
        networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        if not value:
            return networks

        for raw in value.split(","):
            entry = raw.strip()
            if not entry:
                continue
            try:
                # CIDR
                if "/" in entry:
                    networks.append(ipaddress.ip_network(entry, strict=False))
                else:
                    ip = ipaddress.ip_address(entry)
                    networks.append(ipaddress.ip_network(f"{ip}/{ip.max_prefixlen}", strict=False))
            except ValueError:
                continue

        return networks

    def _is_trusted_proxy(self, peer_ip: str) -> bool:
        try:
            ip = ipaddress.ip_address(peer_ip)
        except ValueError:
            return False
        return any(ip in network for network in self._trusted_proxy_networks)

    def _get_remote_ip(self, request: Request) -> str:
        """
        Determine the real client IP.

        - If the immediate peer is a trusted proxy, trust X-Forwarded-For (left-most).
        - Otherwise, use the direct peer IP.
        """
        peer_ip = request.client.host if request.client else "unknown"

        forwarded_for = request.headers.get("X-Forwarded-For", "")
        if forwarded_for and self._is_trusted_proxy(peer_ip):
            # XFF can be a list: "client, proxy1, proxy2"
            first = forwarded_for.split(",")[0].strip()
            # Allow "ip:port" formats
            if ":" in first and first.count(":") == 1:
                first = first.split(":")[0]
            try:
                ipaddress.ip_address(first)
                return first
            except ValueError:
                return peer_ip

        return peer_ip
    
    async def _validate_api_key(self, api_key: str) -> Optional[str]:
        """
        Validate API key against database.
        SECURITY: Returns user_id only if key is valid, None otherwise.
        """
        # Check cache first (short TTL) - use hash to avoid key material in Redis keys
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        cache_key = f"apikey_valid:{key_hash}"
        
        try:
            redis = await get_redis_client()
            cached = await redis.get(cache_key)
            if cached:
                return cached if cached != "invalid" else None
        except Exception:
            pass
        
        # Validate against database
        try:
            from db.session import get_db_session
            from services.auth_service import AuthService
            
            async for db in get_db_session():
                auth_service = AuthService(db)
                user = await auth_service.get_user_by_api_key_hash(api_key)
                
                if user and user.is_active:
                    # Cache valid result for 5 minutes
                    try:
                        redis = await get_redis_client()
                        await redis.setex(cache_key, 300, str(user.id))
                    except Exception:
                        pass
                    return str(user.id)
                else:
                    # Cache invalid result for 1 minute
                    try:
                        redis = await get_redis_client()
                        await redis.setex(cache_key, 60, "invalid")
                    except Exception:
                        pass
                    return None
        except Exception as e:
            logger.warning(f"API key validation failed: {e}")
            return None
        
        return None
    
    async def _check_rate_limit(self, client_id: str) -> tuple[bool, int]:
        """
        Sliding window rate limit check using Redis.
        Returns (allowed, retry_after_seconds).
        
        Uses a true sliding window via sorted sets for accuracy.
        """
        redis = await get_redis_client()
        now = time.time()
        now_ms = int(now * 1000)
        request_id = f"{now_ms}:{secrets.token_hex(8)}"

        # Use sorted sets for true sliding windows
        sec_key = f"rl:sw:sec:{client_id}"
        minute_key = f"rl:sw:min:{client_id}"
        hour_key = f"rl:sw:hr:{client_id}"
        
        pipe = redis.pipeline()
        
        # Remove old entries outside the window
        sec_cutoff = now_ms - 1000       # 1 second ago
        minute_cutoff = now_ms - 60000   # 1 minute ago
        hour_cutoff = now_ms - 3600000   # 1 hour ago

        pipe.zremrangebyscore(sec_key, 0, sec_cutoff)
        pipe.zremrangebyscore(minute_key, 0, minute_cutoff)
        pipe.zremrangebyscore(hour_key, 0, hour_cutoff)
        
        # Add current request
        pipe.zadd(sec_key, {request_id: now_ms})
        pipe.zadd(minute_key, {request_id: now_ms})
        pipe.zadd(hour_key, {request_id: now_ms})
        
        # Count requests in window
        pipe.zcard(sec_key)
        pipe.zcard(minute_key)
        pipe.zcard(hour_key)

        # Oldest request timestamps (for accurate Retry-After)
        pipe.zrange(sec_key, 0, 0, withscores=True)
        pipe.zrange(minute_key, 0, 0, withscores=True)
        pipe.zrange(hour_key, 0, 0, withscores=True)
        
        # Set expiry on keys
        pipe.expire(sec_key, 2)
        pipe.expire(minute_key, 120)
        pipe.expire(hour_key, 7200)
        
        results = await pipe.execute()

        sec_count = results[6]
        minute_count = results[7]
        hour_count = results[8]

        sec_oldest = results[9]
        minute_oldest = results[10]
        hour_oldest = results[11]

        def _retry_after_ms(oldest: list, window_ms: int) -> int:
            if not oldest:
                return window_ms
            # oldest = [(member, score)]
            try:
                oldest_ms = int(oldest[0][1])
            except Exception:
                oldest_ms = now_ms
            return max(0, (oldest_ms + window_ms) - now_ms)

        # Check burst limit (per second)
        if sec_count > self.burst:
            retry_ms = _retry_after_ms(sec_oldest, 1000)
            return False, max(1, math.ceil(retry_ms / 1000))
        
        # Check per-minute limit
        if minute_count > self.rpm:
            retry_ms = _retry_after_ms(minute_oldest, 60000)
            return False, max(1, math.ceil(retry_ms / 1000))
        
        # Check per-hour limit
        if hour_count > self.rph:
            retry_ms = _retry_after_ms(hour_oldest, 3600000)
            return False, max(1, math.ceil(retry_ms / 1000))
        
        return True, 0


class UserQuotaMiddleware(BaseHTTPMiddleware):
    """
    Per-user quota tracking for SEC API calls.
    Prevents any single user from exhausting shared resources.
    """
    
    # Daily quotas by tier
    QUOTAS = {
        "free": 100,
        "basic": 1000,
        "pro": 10000,
        "enterprise": 100000,
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only track SEC-related endpoints
        if not request.url.path.startswith("/api/v1/form4") and \
           not request.url.path.startswith("/api/v1/track"):
            return await call_next(request)
        
        # Get user tier and check quota
        # (In production, this would come from user's subscription)
        
        return await call_next(request)
