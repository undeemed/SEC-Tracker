# SEC-Tracker v2.0 - Architecture Flow

## API Flow (Production)

```mermaid
flowchart TB
    subgraph Clients [CLIENTS]
        Web[Web App]
        Mobile[Mobile App]
        CLI[CLI Tool]
    end

    subgraph LoadBalancer [NGINX]
        LB[Load Balancer<br/>10k conn/worker]
    end

    subgraph API [API LAYER - 4 Replicas]
        direction TB
        Rate[Rate Limiter<br/>60 req/min]
        Auth[Auth<br/>JWT or X-API-Key]
        Routes[FastAPI Routes]
    end

    subgraph Services [SERVICE LAYER]
        AuthSvc[AuthService]
        Form4Svc[Form4Service]
        TrackSvc[TrackingService]
        WatchSvc[WatchlistService]
    end

    subgraph Data [DATA LAYER]
        PG[(PostgreSQL<br/>500 connections)]
        Redis[(Redis<br/>2GB cache)]
    end

    subgraph External [EXTERNAL]
        SEC[SEC EDGAR API]
        AI[OpenRouter AI]
    end

    Clients --> LB
    LB --> Rate
    Rate --> Auth
    Auth --> Routes
    Routes --> Services
    Services --> Data
    Services -.-> External
```

## Request Flow

```mermaid
sequenceDiagram
    participant User
    participant Nginx
    participant API
    participant Redis
    participant DB
    participant SEC

    User->>Nginx: GET /api/v1/form4/AAPL
    Nginx->>API: Load balanced
    API->>Redis: Check rate limit
    Redis-->>API: OK
    API->>Redis: Check cache
    Redis-->>API: Cache miss
    API->>SEC: Fetch Form 4 data
    SEC-->>API: XML response
    Note over API,DB: Form4Service caches responses in Redis.\nPostgreSQL storage is populated via offline migration (scripts/migrate_data.py).
    API->>Redis: Cache result
    API-->>Nginx: JSON response
    Nginx-->>User: 200 OK
```

## Scaling Configuration

| Component | Setting | Handles |
|-----------|---------|---------|
| Nginx | 10k connections/worker | 40k+ concurrent users |
| API | 4 replicas, configurable DB pool | Horizontal scaling |
| PostgreSQL | 500 connections, 2GB cache | High throughput |
| Redis | 2GB LRU cache | Rate limiting + caching |

---

## Related Docs

- [README.md](README.md) - Quick start
- [WALKTHROUGH.md](WALKTHROUGH.md) - Full API reference
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Technical details
