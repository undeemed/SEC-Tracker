# SEC-Tracker

A production-ready SEC filing tracker with **REST API**, **PostgreSQL** storage, and **million-user scale** infrastructure.

## Quick Start (API)

```bash
# Install
pip install -r requirements.txt

# Start services (PostgreSQL + Redis)
docker-compose up -d db redis

# Run migrations
alembic upgrade head

# Start API server
uvicorn api.main:app --host 0.0.0.0 --port 8080

# API docs at http://localhost:8080/docs
```

## Quick Start (CLI)

```bash
# Configure
cat << 'EOF' > .env
SEC_USER_AGENT=Your Name your@email.com
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
| POST | `/api/v1/auth/login` | No | Get JWT token |
| GET | `/api/v1/form4/{ticker}` | No | Insider trading data |
| GET | `/api/v1/form4/` | No | Market-wide activity |
| POST | `/api/v1/track/` | JWT | Start tracking job |
| GET | `/api/v1/watchlist/` | JWT | User's watchlist |
| GET | `/api/v1/health` | No | System health |

## Architecture

```
SEC-Tracker/
├── api/            # FastAPI REST layer
│   ├── routes/     # Endpoints (auth, form4, tracking, watchlist)
│   └── middleware/ # Rate limiting, auth
├── models/         # SQLAlchemy ORM (User, Filing, Transaction)
├── schemas/        # Pydantic validation
├── services/       # Business logic
├── db/             # PostgreSQL + Alembic migrations
├── cache/          # Redis client
├── core/           # Legacy: Tracker, scraper, analyzer
└── docker-compose.yml  # Full stack deployment
```

## Deploy at Scale (Million Users)

```bash
# Start with 4 API replicas + nginx load balancer
docker-compose up -d --scale api=4

# With monitoring (Prometheus + Grafana)
docker-compose --profile monitoring up -d
```

### Scale Configuration
| Component | Setting |
|-----------|---------|
| PostgreSQL | 500 connections, 2GB cache |
| Redis | 2GB LRU cache, 100 conn pool |
| API | 4 replicas, rate limiting |
| Nginx | 10k connections/worker |

## Documentation

- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Full architecture plan
- **[WALKTHROUGH.md](WALKTHROUGH.md)** - API specs and deployment guide
- **[FLOW.md](FLOW.md)** - System flow diagrams

## License

MIT
