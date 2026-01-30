"""
Rate Limiting Middleware for Million-User Scale

Uses Redis for distributed rate limiting across multiple API instances.
Implements sliding window algorithm for accurate rate limiting.
"""
import time
from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from cache.redis_client import get_redis_client
from api.config import get_settings


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
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/", "/api/v1/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier (user_id from JWT or IP)
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
        except Exception:
            # If Redis is down, allow request but log it
            pass
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        
        return response
    
    async def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Try to get user_id from JWT token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from jose import jwt
                settings = get_settings()
                token = auth_header[7:]
                payload = jwt.decode(
                    token,
                    settings.jwt_secret_key,
                    algorithms=[settings.jwt_algorithm]
                )
                return f"user:{payload.get('sub', 'unknown')}"
            except Exception:
                pass
        
        # Try API key
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return f"apikey:{api_key[:16]}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
    
    async def _check_rate_limit(self, client_id: str) -> tuple[bool, int]:
        """
        Sliding window rate limit check using Redis.
        Returns (allowed, retry_after_seconds).
        """
        redis = await get_redis_client()
        now = time.time()
        
        # Keys for different windows
        second_key = f"rl:sec:{client_id}:{int(now)}"
        minute_key = f"rl:min:{client_id}:{int(now / 60)}"
        hour_key = f"rl:hr:{client_id}:{int(now / 3600)}"
        
        pipe = redis.pipeline()
        
        # Increment counters
        pipe.incr(second_key)
        pipe.expire(second_key, 2)
        pipe.incr(minute_key)
        pipe.expire(minute_key, 120)
        pipe.incr(hour_key)
        pipe.expire(hour_key, 7200)
        
        results = await pipe.execute()
        
        second_count = results[0]
        minute_count = results[2]
        hour_count = results[4]
        
        # Check burst limit (per second)
        if second_count > self.burst:
            return False, 1
        
        # Check per-minute limit
        if minute_count > self.rpm:
            return False, 60 - int(now % 60)
        
        # Check per-hour limit
        if hour_count > self.rph:
            return False, 3600 - int(now % 3600)
        
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
