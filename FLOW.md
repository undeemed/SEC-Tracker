# SEC Filing Tracker - Flow

A concise, high-level flow diagram. For setup, commands, and integration details, see `README.md` and `WALKTHROUGH.md`.

## System Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  REQUEST                                     │
│                                                                             │
│   python run.py track AAPL                                                  │
│   python run.py form4 NVDA -r 20                                            │
│   python run.py latest 50 -hp                                               │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               run.py                                         │
│                           (CLI Router)                                       │
│                                                                             │
│   Routes commands to core/ and services/ modules                             │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌─────────────────────────┐ ┌──────────────────────┐ ┌────────────────────────┐
│       core/             │ │      services/       │ │        utils/          │
├─────────────────────────┤ ├──────────────────────┤ ├────────────────────────┤
│  tracker.py             │ │ form4_company.py     │ │  common.py             │
│    ├─▶ scraper.py ─▶ SEC│ │ form4_market.py      │ │  config.py             │
│    ├─▶ downloader.py    │ │ monitor.py           │ │  api_keys.py           │
│    └─▶ analyzer.py ─▶ AI│ └──────────────────────┘ │  cik.py                │
└─────────────────────────┘                          └────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  OUTPUT                                     │
│                                                                             │
│   • Downloaded filings in sec_filings/{TICKER}/                             │
│   • AI analysis in analysis_results/{TICKER}/                               │
│   • Cached data in cache/                                                   │
│   • Console output with formatted tables                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Related Docs

- `README.md` for quick start and commands
- `WALKTHROUGH.md` for integration and API formats

---

## License

MIT
