# SEC-Tracker

A production-ready SEC filing tracker with a **REST API**, **PostgreSQL** for multi-user state, and **Redis** for caching + rate limiting.

## Quick Start (API)

```bash
# Install
pip install -r requirements.txt

# Start local dev stack (PostgreSQL + Redis + API on http://localhost:8080)
# NOTE: `docker-compose.dev.yml` is for development only (it exposes DB/Redis ports).
docker-compose -f docker-compose.dev.yml up -d

# Run migrations
alembic upgrade head

# API docs at http://localhost:8080/docs
```

## Quick Start (CLI)

```bash
# Configure
cat << 'EOF' > .env
SEC_USER_AGENT=Your Name your@email.com
# Optional (only needed for AI analysis features)
OPENROUTER_API_KEY=sk-or-v1-...
EOF

# Run CLI commands
python run.py track AAPL           # Track company filings
python run.py form4 NVDA -r 20     # Insider trading
python run.py latest 50            # Market-wide activity
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/register` | No | User registration |
| POST | `/api/v1/auth/login` | No | Get JWT access + refresh token |
| POST | `/api/v1/auth/refresh` | No | Refresh tokens (body: `{refresh_token}`) |
| POST | `/api/v1/auth/api-key` | JWT | Generate API key *(returned once)* |
| GET | `/api/v1/form4/{ticker}` | Optional | Insider trading data |
| GET | `/api/v1/form4/` | Optional | Market-wide activity |
| POST | `/api/v1/track/` | JWT or `X-API-Key` | Start tracking job |
| GET | `/api/v1/watchlist/` | JWT or `X-API-Key` | User's watchlist |
| GET | `/api/v1/health` | No | System health |

More endpoints (tracking history, watchlist activity/search, etc.) are documented in `WALKTHROUGH.md`.

## Architecture

```
SEC-Tracker/
├── api/            # FastAPI REST layer
│   ├── routes/     # Endpoints (auth, form4, tracking, watchlist)
│   └── middleware/ # Rate limiting, auth
├── models/         # SQLAlchemy ORM (users, jobs, watchlists, etc.)
├── schemas/        # Pydantic validation
├── services/       # Business logic
├── db/             # PostgreSQL + Alembic migrations
├── cache/          # Redis client
├── core/           # Legacy: Tracker, scraper, analyzer
├── docker-compose.yml      # Production stack (nginx + API + DB + Redis)
├── docker-compose.dev.yml  # Dev stack (exposes ports)
├── nginx.conf              # TLS + load balancing
└── scripts/preflight.py    # Production config checks
```

## Deploy at Scale 

```bash
# Production stack requires secrets and TLS certs (see `ssl/README.md`).
# Required env vars:
#   DB_PASSWORD, JWT_SECRET_KEY, SEC_USER_AGENT
# TLS certs expected at:
#   ssl/fullchain.pem, ssl/privkey.pem

# Optional: run preflight checks
python scripts/preflight.py

# Start with 4 API replicas + nginx load balancer (HTTPS)
docker-compose up -d --scale api=4

# With monitoring (Prometheus + Grafana)
docker-compose --profile monitoring up -d

# With background workers (Celery)
docker-compose --profile with-worker up -d
```

### Data Storage Notes
- Form 4 endpoints fetch from SEC and cache results in Redis. Persisting filings/transactions into PostgreSQL is supported via `scripts/migrate_data.py` (for migrating existing local cache/state).

### AI Analysis (OpenRouter)
- Required: `OPENROUTER_API_KEY`
- Model selection: `OPENROUTER_MODEL` (single model)
- Model rotation: `OPENROUTER_MODEL_ROTATION="modelA,modelB"` or `OPENROUTER_MODEL_SLOT_1..9`
- Per-request override: `POST /api/v1/track/analyze/{filing_id}?model_slot=2`
- Per-request model override: `POST /api/v1/track/analyze/{filing_id}?model=openai/gpt-4.1-mini`

### Scale Configuration
| Component | Setting |
|-----------|---------|
| PostgreSQL | 500 connections, 2GB cache |
| Redis | 2GB LRU cache, configurable conn pool |
| API | 4 replicas, rate limiting |
| Nginx | 10k connections/worker |

## Documentation

- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Full architecture plan
- **[WALKTHROUGH.md](WALKTHROUGH.md)** - API specs and deployment guide
- **[FLOW.md](FLOW.md)** - System flow diagrams

## License

MIT
