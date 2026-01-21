# SEC Filing Tracker - Flow

A concise, high-level flow diagram. For setup, commands, and integration details, see `README.md` and `WALKTHROUGH.md`.

## System Flow

```mermaid
flowchart TB
    subgraph Request [REQUEST]
        direction TB
        R1[python run.py track AAPL]
        R2[python run.py form4 NVDA -r 20]
        R3[python run.py latest 50 -hp]
    end

    Router[run.py<br/>CLI Router]

    subgraph Core [core/]
        Tracker[tracker.py]
        Scraper[scraper.py]
        Downloader[downloader.py]
        Analyzer[analyzer.py]
    end

    subgraph Services [services/]
        Form4Co[form4_company.py]
        Form4Mkt[form4_market.py]
        Monitor[monitor.py]
    end

    subgraph Utils [utils/]
        Common[common.py]
        Config[config.py]
        APIKeys[api_keys.py]
        CIK[cik.py]
    end

    subgraph Output [OUTPUT]
        direction TB
        O1[Downloaded filings]
        O2[AI analysis]
        O3[Cached data]
        O4[Console output]
    end

    External[SEC API / AI]

    Request --> Router
    Router --> Tracker
    Router --> Form4Co
    Router --> Form4Mkt
    Router --> Monitor

    Tracker --> Scraper
    Tracker --> Downloader
    Tracker --> Analyzer

    Scraper -.-> External
    Analyzer -.-> External

    Tracker --> Output
    Form4Co --> Output
    Form4Mkt --> Output
```

## Related Docs

- `README.md` for quick start and commands
- `WALKTHROUGH.md` for integration and API formats

---

## License

MIT
