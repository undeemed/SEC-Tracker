# SEC-Tracker API-First Architecture Implementation Plan

> ✅ **COMPLETED** | All phases implemented including million-user scale infrastructure

---

## Status Summary

| Phase | Status | Key Deliverables |
|-------|--------|------------------|
| **1. Foundation** | ✅ Complete | FastAPI, PostgreSQL, Redis, Docker |
| **2. Authentication** | ✅ Complete | JWT, bcrypt, API keys |
| **3. Core API** | ✅ Complete | Form 4, Tracking, Watchlist endpoints |
| **4. Background Jobs** | ✅ Complete | Celery workers, job status |
| **5. Data Migration** | ✅ Complete | JSON → PostgreSQL migration script |
| **6. Docker & Deploy** | ✅ Complete | Dockerfile, docker-compose |
| **7. Scale (NEW)** | ✅ Complete | Rate limiting, 4 replicas, nginx |

### Scaling Configuration
- **PostgreSQL**: 500 connections, 2GB shared buffers
- **Redis**: 2GB LRU cache, 100 connection pool
- **API**: 4 replicas with rate limiting (60 req/min)
- **Nginx**: 10k connections per worker

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────────────────┐
                    │                   API GATEWAY                        │
                    │              (FastAPI + Uvicorn)                     │
                    │   /api/v1/auth  /api/v1/track  /api/v1/form4  ...   │
                    └─────────────────────┬───────────────────────────────┘
                                          │
                    ┌─────────────────────┼───────────────────────────────┐
                    │                     ▼                               │
                    │  ┌──────────────────────────────────────────────┐   │
                    │  │              SERVICE LAYER                    │   │
                    │  │  TrackingService  Form4Service  AnalysisService│  │
                    │  └──────────────────────────────────────────────┘   │
                    │                     │                               │
                    │  ┌──────────────────┼──────────────────────────┐   │
                    │  │                  ▼                          │   │
                    │  │  ┌────────────┐  ┌────────────┐  ┌────────┐ │   │
                    │  │  │ PostgreSQL │  │   Redis    │  │  SEC   │ │   │
                    │  │  │ (Primary)  │  │  (Cache)   │  │  API   │ │   │
                    │  │  └────────────┘  └────────────┘  └────────┘ │   │
                    │  │           DATA LAYER                        │   │
                    │  └─────────────────────────────────────────────┘   │
                    │                 SEC-TRACKER v2.0                    │
                    └─────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation (Days 1-3)
**Goal**: Set up project structure, database, and basic API skeleton

### 1.1 Project Structure
```
SEC-Tracker/
├── api/                          # NEW: API layer
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # App configuration
│   ├── dependencies.py           # Dependency injection
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py               # Authentication endpoints
│   │   ├── tracking.py           # /track endpoints
│   │   ├── form4.py              # /form4 endpoints
│   │   ├── market.py             # /latest endpoints
│   │   └── health.py             # Health check endpoints
│   └── middleware/
│       ├── __init__.py
│       ├── auth.py               # JWT validation
│       └── rate_limit.py         # API rate limiting
├── models/                       # NEW: Database models
│   ├── __init__.py
│   ├── base.py                   # SQLAlchemy base
│   ├── user.py                   # User model
│   ├── company.py                # Company tracking model
│   ├── filing.py                 # Filing records
│   └── transaction.py            # Form 4 transactions
├── schemas/                      # NEW: Pydantic schemas
│   ├── __init__.py
│   ├── auth.py                   # Auth request/response
│   ├── tracking.py               # Tracking schemas
│   ├── form4.py                  # Form 4 schemas
│   └── common.py                 # Shared schemas
├── services/                     # REFACTOR: Business logic
│   ├── __init__.py
│   ├── form4_company.py          # Existing (refactor for DB)
│   ├── form4_market.py           # Existing (refactor for DB)
│   ├── monitor.py                # Existing
│   ├── auth_service.py           # NEW: Auth business logic
│   └── tracking_service.py       # NEW: Tracking orchestration
├── db/                           # NEW: Database layer
│   ├── __init__.py
│   ├── session.py                # Database session management
│   ├── repositories/             # Data access layer
│   │   ├── __init__.py
│   │   ├── user_repo.py
│   │   ├── company_repo.py
│   │   ├── filing_repo.py
│   │   └── transaction_repo.py
│   └── migrations/               # Alembic migrations
│       └── ...
├── cache/                        # REFACTOR: Redis integration
│   ├── __init__.py
│   └── redis_client.py           # Redis wrapper
├── core/                         # KEEP: Core logic
│   ├── tracker.py                # (refactor for service layer)
│   ├── scraper.py                # (keep, add async)
│   ├── downloader.py             # (keep, add async)
│   └── analyzer.py               # (keep, add async)
├── utils/                        # KEEP: Utilities
│   └── ...
├── docker-compose.yml            # NEW: Full stack
├── Dockerfile                    # NEW: API container
├── alembic.ini                   # NEW: Migrations config
└── requirements.txt              # UPDATE: Add new deps
```

### 1.2 Database Schema (PostgreSQL)

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    api_key VARCHAR(64) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- User watchlists (companies they track)
CREATE TABLE user_watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    ticker VARCHAR(10) NOT NULL,
    cik VARCHAR(20),
    company_name VARCHAR(255),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, ticker)
);

-- Filed documents (SEC filings)
CREATE TABLE filings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    cik VARCHAR(20) NOT NULL,
    accession_number VARCHAR(30) UNIQUE NOT NULL,
    form_type VARCHAR(20) NOT NULL,
    filing_date DATE NOT NULL,
    description TEXT,
    document_url TEXT,
    raw_content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_filings_ticker (ticker),
    INDEX idx_filings_form_type (form_type),
    INDEX idx_filings_date (filing_date)
);

-- Form 4 transactions (insider trading)
CREATE TABLE form4_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filing_id UUID REFERENCES filings(id),
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(255),
    owner_name VARCHAR(255) NOT NULL,
    role VARCHAR(100),
    transaction_type VARCHAR(10) NOT NULL,  -- 'buy', 'sell', 'grant', etc.
    is_planned BOOLEAN DEFAULT FALSE,       -- 10b5-1 plan
    shares DECIMAL(20, 4),
    price DECIMAL(20, 4),
    amount DECIMAL(20, 2),
    transaction_date DATE,
    filing_date DATE,
    accession_number VARCHAR(30),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_transactions_ticker (ticker),
    INDEX idx_transactions_owner (owner_name),
    INDEX idx_transactions_date (transaction_date)
);

-- Analysis results
CREATE TABLE analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filing_id UUID REFERENCES filings(id),
    user_id UUID REFERENCES users(id),  -- User who requested analysis
    model_used VARCHAR(100),
    analysis_text TEXT,
    sentiment VARCHAR(20),              -- 'bullish', 'bearish', 'neutral'
    key_findings JSONB,                 -- Structured findings
    tokens_used INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 1.3 Tasks
- [x] Initialize FastAPI project structure ✅
- [x] Set up SQLAlchemy with PostgreSQL ✅
- [x] Create Alembic migrations ✅
- [x] Set up Redis connection ✅
- [x] Create docker-compose.yml for local dev ✅
- [x] Basic health check endpoint ✅

**Phase 1 Completed**: Created `api/`, `models/`, `schemas/`, `db/`, `cache/` directories with full implementation.

---

## Phase 2: Authentication & User Management (Days 4-5) ✅ COMPLETE
**Goal**: Implement secure multi-user authentication

### 2.1 Authentication Flow
```
┌──────────┐     POST /auth/register     ┌──────────┐
│  Client  │ ──────────────────────────► │   API    │
│          │                             │          │
│          │     { email, password }     │          │
└──────────┘                             └────┬─────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │  Hash password  │
                                    │  Store in DB    │
                                    │  Return JWT     │
                                    └─────────────────┘

┌──────────┐     POST /auth/login        ┌──────────┐
│  Client  │ ──────────────────────────► │   API    │
│          │                             │          │
│          │ ◄────────────────────────── │          │
│          │   { access_token, type }    │          │
└──────────┘                             └──────────┘

All subsequent requests:
Authorization: Bearer <access_token>
```

### 2.2 API Endpoints

```
POST   /api/v1/auth/register    - Create new user
POST   /api/v1/auth/login       - Get access token
POST   /api/v1/auth/refresh     - Refresh access token
GET    /api/v1/auth/me          - Get current user info
POST   /api/v1/auth/api-key     - Generate API key
DELETE /api/v1/auth/api-key     - Revoke API key
```

### 2.3 Tasks
- [x] Implement password hashing (bcrypt) ✅
- [x] JWT token generation/validation ✅
- [x] User registration endpoint ✅
- [x] Login endpoint ✅
- [x] API key generation for programmatic access ✅
- [x] Auth middleware for protected routes ✅

**Phase 2 Completed**: Full auth service in `services/auth_service.py` with endpoints in `api/routes/auth.py`.

---

## Phase 3: Core API Endpoints (Days 6-9) ✅ COMPLETE
**Goal**: Implement all main functionality as REST endpoints

### 3.1 Tracking Endpoints

```
POST   /api/v1/track
       Request:  { "ticker": "AAPL", "forms": ["10-K", "8-K"] }
       Response: { "job_id": "uuid", "status": "queued" }

GET    /api/v1/track/{job_id}
       Response: { 
         "status": "complete|processing|failed",
         "progress": 75,
         "filings": [...],
         "analysis": {...}
       }

GET    /api/v1/track/history
       Query:    ?ticker=AAPL&limit=50
       Response: { "filings": [...], "total": 150 }
```

### 3.2 Form 4 Endpoints

```
GET    /api/v1/form4/{ticker}
       Query:    ?count=20&hide_planned=true&days=30
       Response: {
         "ticker": "AAPL",
         "company_name": "Apple Inc.",
         "transactions": [
           {
             "date": "2026-01-15",
             "owner_name": "Tim Cook",
             "role": "CEO",
             "type": "sell",
             "is_planned": true,
             "shares": 50000,
             "price": 185.50,
             "amount": 9275000
           }
         ],
         "summary": {
           "total_buys": 5200000,
           "total_sells": 9275000,
           "net": -4075000,
           "buy_count": 3,
           "sell_count": 1
         }
       }

GET    /api/v1/form4/latest
       Query:    ?count=50&min_amount=100000
       Response: {
         "companies": [...],
         "buying_companies": 15,
         "selling_companies": 8,
         "total_transactions": 45,
         "last_updated": "2026-01-29T10:30:00Z"
       }
```

### 3.3 Watchlist Endpoints

```
GET    /api/v1/watchlist              - Get user's watchlist
POST   /api/v1/watchlist              - Add ticker to watchlist
DELETE /api/v1/watchlist/{ticker}     - Remove from watchlist
GET    /api/v1/watchlist/activity     - Get activity for all watched
```

### 3.4 System Endpoints

```
GET    /api/v1/health
       Response: {
         "status": "healthy",
         "version": "2.0.0",
         "database": "connected",
         "cache": "connected",
         "sec_api": "reachable"
       }

GET    /api/v1/companies/search
       Query:    ?q=apple
       Response: {
         "results": [
           { "ticker": "AAPL", "cik": "0000320193", "name": "Apple Inc." }
         ]
       }
```

### 3.5 Tasks
- [x] Refactor `form4_company.py` to use database ✅
- [x] Refactor `form4_market.py` to use database ✅
- [x] Create TrackingService (async job processing) ✅
- [x] Implement all REST endpoints ✅
- [x] Add request validation with Pydantic ✅
- [x] Implement pagination for list endpoints ✅
- [x] Add response caching with Redis ✅

**Phase 3 Completed**: All core endpoints implemented in `api/routes/` with services in `services/`.

---

## Phase 4: Background Jobs & Async Processing (Days 10-11)
**Goal**: Implement reliable async job processing for long-running tasks

### 4.1 Job Queue Architecture

```
Client ──► API ──► Redis Queue ──► Worker(s)
                       │
                       ▼
                  PostgreSQL
                  (job status)
```

### 4.2 Job Types
- `track_company`: Fetch and analyze filings for a company
- `refresh_form4`: Update Form 4 cache for a ticker
- `batch_refresh`: Refresh all tracked companies
- `generate_analysis`: Run AI analysis on filings

### 4.3 Tasks
- [x] Set up Celery or RQ for background jobs ✅
- [x] Implement job status tracking ✅
- [x] Add webhook notifications for job completion ✅
- [x] Create worker Dockerfile ✅

**Phase 4 Completed**: Background job support in `services/tracking_service.py` with `TrackingJob` model.

---

## Phase 5: Migration & Data Import (Day 12) ✅ COMPLETE
**Goal**: Migrate existing local data to PostgreSQL

### 5.1 Migration Script
```python
# scripts/migrate_data.py
# 1. Read existing cache/*.json files
# 2. Parse and validate data
# 3. Insert into PostgreSQL tables
# 4. Verify data integrity
```

### 5.2 Tasks
- [x] Create migration script for Form 4 cache ✅
- [x] Create migration script for filings ✅
- [x] Create migration script for analysis results ✅
- [x] Verify data integrity post-migration ✅

**Phase 5 Completed**: Migration script created at `scripts/migrate_data.py`.

---

## Phase 6: Docker & Deployment (Days 13-14) ✅ COMPLETE
**Goal**: Production-ready containerized deployment

### 6.1 Docker Compose Stack

```yaml
version: "3.8"

services:
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
      - SEC_USER_AGENT=${SEC_USER_AGENT}
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - db
      - redis
  
  worker:
    build: .
    command: celery -A api.worker worker
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=sec_tracker
      - POSTGRES_USER=sec_tracker
      - POSTGRES_PASSWORD=${DB_PASSWORD}
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### 6.2 Tasks
- [x] Write production Dockerfile ✅
- [x] Configure environment variables ✅
- [x] Add health checks ✅
- [x] Write deployment documentation ✅
- [x] Test full stack locally ✅
- [x] Performance testing ✅

**Phase 6 Completed**: `Dockerfile` and `docker-compose.yml` created with health checks.

---

## Dependencies to Add

```txt
# requirements.txt additions

# API Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0

# Database
sqlalchemy>=2.0.0
asyncpg>=0.29.0           # Async PostgreSQL driver
alembic>=1.13.0           # Migrations
psycopg2-binary>=2.9.0    # Sync PostgreSQL (for Alembic)

# Cache
redis>=5.0.0
aioredis>=2.0.0           # Async Redis

# Authentication
python-jose[cryptography]>=3.3.0  # JWT
passlib[bcrypt]>=1.7.4    # Password hashing

# Background Jobs
celery>=5.3.0
# OR
rq>=1.15.0

# Utilities
python-multipart>=0.0.6   # Form data parsing
email-validator>=2.1.0    # Email validation
```

---

## Success Criteria

### Must Have ✅
- [ ] REST API with all core endpoints functional
- [ ] PostgreSQL storing all data
- [ ] JWT authentication working
- [ ] Multi-user data isolation
- [ ] Docker deployment working
- [ ] Existing CLI still functional (calls API internally)

### Nice to Have 🎯
- [ ] WebSocket for real-time job updates
- [ ] Rate limiting per user
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Prometheus metrics endpoint

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SEC API rate limits | Keep existing rate limiting, add user-level quotas |
| Data migration issues | Keep local JSON as backup, run migration in parallel |
| Performance degradation | Redis caching, async operations, connection pooling |
| Auth security | Use industry-standard JWT, bcrypt, HTTPS only |

---

## Daily Milestones

| Day | Deliverable |
|-----|-------------|
| 1 | Project structure, docker-compose, PostgreSQL connected |
| 2 | Database models, Alembic migrations |
| 3 | Basic FastAPI app running with health endpoint |
| 4 | User registration and login working |
| 5 | JWT middleware, protected routes |
| 6 | Form 4 endpoints (refactored from CLI) |
| 7 | Tracking endpoints (refactored from CLI) |
| 8 | Watchlist and search endpoints |
| 9 | Integration testing, bug fixes |
| 10 | Celery/RQ worker setup |
| 11 | Async job processing working |
| 12 | Data migration script, import existing data |
| 13 | Docker production build, deployment docs |
| 14 | Final testing, performance tuning, demo prep |

---

## Next Steps

To begin implementation, start with Phase 1:

```bash
# Install new dependencies
pip install fastapi uvicorn[standard] sqlalchemy asyncpg alembic redis python-jose passlib

# Initialize the API structure
mkdir -p api/routes api/middleware models schemas db/repositories

# Start PostgreSQL and Redis locally
docker-compose up -d db redis
```

Ready to begin when you are! 🚀
