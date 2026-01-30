#!/usr/bin/env python3
"""
Preflight checks for production deployments.

This script is intentionally conservative: it tries to catch common misconfigurations
that lead to insecure deployments or runtime failures.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    # Import lazily so env vars are loaded first
    from api.config import get_settings

    settings = get_settings()

    # Required secrets / identifiers
    if not settings.sec_user_agent:
        errors.append("SEC_USER_AGENT is required (SEC EDGAR requires contact info).")
    elif "@" not in settings.sec_user_agent:
        warnings.append("SEC_USER_AGENT does not appear to contain an email address.")

    if not settings.jwt_secret_key or len(settings.jwt_secret_key) < 32:
        errors.append("JWT_SECRET_KEY must be set and at least 32 characters.")

    if settings.jwt_secret_key in {
        "CHANGE_ME_IN_PRODUCTION_32_CHARS_MIN",
        "dev_secret_key_change_in_production",
    }:
        errors.append("JWT_SECRET_KEY is set to an unsafe default.")

    # Database/Redis URLs sanity checks (best-effort)
    if "localhost" in settings.database_url:
        warnings.append("DATABASE_URL points at localhost (likely wrong inside containers).")

    if "sec_tracker:sec_tracker@" in settings.database_url:
        warnings.append("DATABASE_URL appears to use a default password (do not use in production).")

    if "localhost" in settings.redis_url:
        warnings.append("REDIS_URL points at localhost (likely wrong inside containers).")

    # TLS certs (only if present in repo/expected by nginx.conf)
    ssl_dir = Path("ssl")
    if ssl_dir.exists():
        fullchain = ssl_dir / "fullchain.pem"
        privkey = ssl_dir / "privkey.pem"
        if not fullchain.exists() or not privkey.exists():
            warnings.append("TLS certs missing: expected ssl/fullchain.pem and ssl/privkey.pem for nginx 443.")

    # Celery (optional)
    celery_enabled = _is_truthy(os.getenv("CELERY_ENABLED")) or bool(getattr(settings, "celery_enabled", False))
    if celery_enabled:
        try:
            import celery  # noqa: F401
        except Exception as e:  # pragma: no cover
            errors.append(f"CELERY_ENABLED is true but Celery import failed: {e}")

    # OpenRouter (optional, required for analysis endpoints)
    openrouter_key = os.getenv("OPENROUTER_API_KEY") or getattr(settings, "openrouter_api_key", None)
    model_rotation = (os.getenv("OPENROUTER_MODEL_ROTATION") or "").strip()
    if openrouter_key:
        models: list[str] = []
        if model_rotation:
            models = [m.strip() for m in model_rotation.split(",") if m.strip()]
            if not models:
                errors.append("OPENROUTER_MODEL_ROTATION is set but empty after parsing.")
        else:
            for i in range(1, 10):
                raw = (os.getenv(f"OPENROUTER_MODEL_SLOT_{i}") or "").strip()
                if raw:
                    models.append(raw)
            if not models:
                single = (os.getenv("OPENROUTER_MODEL") or getattr(settings, "openrouter_model", "") or "").strip()
                if single:
                    models = [single]

        if not models:
            warnings.append(
                "OPENROUTER_API_KEY is set but no model is configured. "
                "Set OPENROUTER_MODEL, OPENROUTER_MODEL_ROTATION, or OPENROUTER_MODEL_SLOT_1..9."
            )

        extra_headers = (os.getenv("OPENROUTER_EXTRA_HEADERS_JSON") or "").strip()
        if extra_headers:
            try:
                import json

                json.loads(extra_headers)
            except Exception as e:
                errors.append(f"OPENROUTER_EXTRA_HEADERS_JSON is not valid JSON: {e}")

    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"- {w}")

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"- {e}")
        return 1

    print("Preflight OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
