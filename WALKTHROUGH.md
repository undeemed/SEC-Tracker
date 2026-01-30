# SEC Filing Tracker - Technical Walkthrough

> **For Integration Partners**: Complete API documentation for SEC-Tracker v2.0

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [REST API Reference](#rest-api-reference)
3. [Authentication](#authentication)
4. [Scaling Architecture](#scaling-architecture)
5. [Legacy CLI](#legacy-cli)

---

## Quick Start

### API Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL + Redis
docker-compose up -d db redis

# Run migrations
alembic upgrade head

# Start API
uvicorn api.main:app --host 0.0.0.0 --port 8080
```

API docs: `http://localhost:8080/docs`

### Docker (Full Stack)

```bash
# Start all services
docker-compose up -d

# Scale for production
docker-compose up -d --scale api=4
```

---

## REST API Reference

### Authentication

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/api/v1/auth/register` | POST | `{email, password}` | `{access_token, refresh_token}` |
| `/api/v1/auth/login` | POST | `{email, password}` | `{access_token, refresh_token}` |
| `/api/v1/auth/refresh` | POST | `{refresh_token}` | `{access_token}` |
| `/api/v1/auth/api-key` | POST | (Bearer token) | `{api_key}` |

### Form 4 Insider Trading

```bash
# Get company insider activity
GET /api/v1/form4/{ticker}?days=30&count=50

# Response
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "transactions": [...],
  "summary": {
    "total_buys": 5000000,
    "total_sells": 2000000,
    "net": 3000000,
    "buy_count": 5,
    "sell_count": 2
  }
}
```

```bash
# Market-wide activity
GET /api/v1/form4/

# Response
{
  "companies": [...],
  "total_companies": 50,
  "buying_companies": 30,
  "selling_companies": 20
}
```

### Tracking

```bash
# Start tracking job (requires auth)
POST /api/v1/track/
{
  "ticker": "AAPL",
  "forms": ["10-K", "8-K"]
}

# Response
{
  "job_id": "abc123",
  "status": "pending"
}
```

```bash
# Check job status
GET /api/v1/track/{job_id}

# Response
{
  "job_id": "abc123",
  "status": "complete",
  "result": {...}
}
```

### Watchlist

```bash
# Get user watchlist (requires auth)
GET /api/v1/watchlist/

# Add to watchlist
POST /api/v1/watchlist/
{"ticker": "NVDA"}

# Remove from watchlist
DELETE /api/v1/watchlist/{ticker}
```

### Health Check

```bash
GET /api/v1/health

{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

---

## Authentication

### JWT Tokens

```bash
# Get token
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret"}'

# Use token
curl http://localhost:8080/api/v1/watchlist/ \
  -H "Authorization: Bearer <access_token>"
```

### API Keys

```bash
# Generate API key
curl -X POST http://localhost:8080/api/v1/auth/api-key \
  -H "Authorization: Bearer <access_token>"

# Use API key
curl http://localhost:8080/api/v1/watchlist/ \
  -H "X-API-Key: <api_key>"
```

---

## Scaling Architecture

### Million-User Configuration

| Component | Config | Purpose |
|-----------|--------|---------|
| **PostgreSQL** | 500 max_connections, 2GB shared_buffers | High-concurrency DB |
| **Redis** | 2GB maxmemory, LRU eviction | Rate limiting + cache |
| **API** | 4 replicas, 100 pool connections | Horizontal scaling |
| **Nginx** | 10k connections/worker | Load balancing |

### Deploy Command

```bash
# Start with 4 API replicas
docker-compose up -d --scale api=4

# With monitoring
docker-compose --profile monitoring up -d
```

### Rate Limits

| Tier | Per Minute | Per Hour | Burst |
|------|------------|----------|-------|
| Default | 60 | 1000 | 10/sec |

---

## Legacy CLI

The CLI still works for local usage:

```bash
python run.py track AAPL           # Track company filings
python run.py form4 NVDA -r 20     # Insider trading
python run.py latest 50            # Market-wide activity
python run.py monitor --json       # System status
```

---

## Module Summary

| Layer | Modules |
|-------|---------|
| **API** | `api/main.py`, `api/routes/`, `api/middleware/` |
| **Services** | `services/auth_service.py`, `form4_service.py`, `tracking_service.py` |
| **Models** | `models/user.py`, `filing.py`, `transaction.py` |
| **Database** | `db/session.py`, `db/migrations/` |
| **Cache** | `cache/redis_client.py` |
| **Core** | `core/tracker.py`, `scraper.py`, `analyzer.py` |
