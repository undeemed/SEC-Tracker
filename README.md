# SEC Filing Tracker - Multi-Company Support

## Overview

Enhanced SEC filing system that works with any publicly traded company using ticker symbols. The main command `track` handles everything intelligently.

## Quick Start

### 1. Setup
```bash
# Install dependencies
pip install requests tiktoken openai python-dotenv tqdm

# Runner
python run.py 'command' 'ticker'
```

### 2. API Key Setup (Required for Full Functionality)

This application requires API keys for SEC data access and AI analysis features. **The application will prompt you for these inputs when needed**, but you can also set them up in advance.

#### Option A: Interactive Setup (Recommended)
The application will automatically prompt you for required information when you first run commands that need it:

1. **SEC User Agent**: When you first run a command that accesses SEC data, you'll be prompted to enter:
   - Your name
   - Your email address
   - The application will format this as "Your Name your-email@example.com"

2. **OpenAI API Key**: When you first run analysis commands, you'll be prompted to enter:
   - Your OpenAI API key (or OpenRouter API key)
   - This enables AI-powered analysis of SEC filings

#### Option B: Manual Setup (Advanced)
You can also configure these manually by creating a `.env` file:

1. **Get Your API Keys**:
   - **OPENROUTER_API_KEY**: Sign up at [https://openrouter.ai/](https://openrouter.ai/) to get your API key for AI analysis
      - Note: when using a free api key you will somtimes hit rate limit. 
   - **SEC_USER_AGENT**: Use your own contact information in the format "Your Name your-email@example.com"

2. **Configure Your API Keys**:
   ```bash   
   # Edit the .env file with your actual API keys
   nano .env  # or use your preferred text editor
   ```

3. **Update the .env File**:
   Replace the example values in `.env` with your actual keys:
   ```
   # SEC User Agent (required for SEC API access)
   SEC_USER_AGENT=Your Name your-email@example.com
   
   # OPEN ROUTER API Key (for AI analysis features)
   OPENROUTER_API_KEY=your-actual-openrouter-api-key-here
   ```

   Note: The `.env` file is gitignored and will not be committed to version control.

### 3. Primary Usage - Track Command

`track` is the main command that does everything:
```bash
track AAPL    # Validates ticker → Downloads new filings → Analyzes changes
track TSLA    # Smart update for Tesla
track MSFT    # Smart update for Microsoft
```

**What `track` does:**
- ✓ Validates ticker & gets CIK automatically
- ✓ Downloads ONLY new filings (skips existing)
- ✓ Analyzes ONLY forms with new content
- ✓ Maintains state for efficient updates

### 4. Track Options
```bash
track AAPL --check-only        # Preview what's new without downloading
track TSLA --force-download    # Force re-download everything
track MSFT --force-analysis    # Force re-analyze all forms
track summary                  # Show all tracked companies
track --list-companies         # List companies you're tracking
```

## Common Workflows

### New Company
```bash
# Just run track - it handles everything!
track GOOGL
```

### Daily Updates
```bash
# Update single company
track AAPL

# Update all tracked companies
multi update-all
```

### Portfolio Setup
Create `portfolio.txt`:
```
AAPL
MSFT
GOOGL
TSLA
NVDA
```

Then:
```bash
multi add-list portfolio.txt
multi update-all
```

## Other Commands (Optional)

While `track` handles most needs, these commands are available for specific tasks:

```bash
scan AAPL              # Look up company info only
scan search "tesla"    # Search for companies

fetch TSLA             # Preview available filings
download MSFT 10-K     # Force download specific forms
analyze GOOGL          # Force re-analyze

monitor                # System dashboard / usage
monitor --alerts       # Check for critical updates
```

## Form 4 Insider Trading Tracker

Track real-time insider trading activity with intelligent caching and filtering:

### First-Time Setup (Required)
```bash
# Build the cache first (this fetches ~500 recent Form 4 filings)
latest 50                      # Shows 50 companies, builds cache
```

### Filtering (After Cache is Built)
```bash                        
latest 30 -hp                  # Hide planned transactions
latest 40 -min 100000          # Companies with net activity >= $100K
latest 25 -min +500000         # Companies with total buys >= $500K
latest 200 -min -1000000 -hp   # 200 companies with sells >= $1M, no planned
latest 15 -m                   # Sort by most active (transaction count)
latest 50 --refresh            # Force refresh cache and fetch new data
```

**Important:** You must build the cache first before using any filters!

**Filters (applied at company level):**
- `-hp`: Hide planned (10b5-1) transactions
- `-min X`: Only show companies with net activity >= $X (absolute value)
- `-min +X`: Only show companies with total buys >= $X
- `-min -X`: Only show companies with total sells >= $X
- `-m`: Sort by most active (highest transaction count)
- `--refresh`: Force refresh cache (bypasses cache requirement)

**Caching System:**
- ✅ **Smart Caching**: Stores complete transaction data (not just URLs)
- ✅ **Instant Filtering**: All filters work instantly on cached data
- ✅ **Progress Bar**: Real-time progress during initial data fetch
- ✅ **Rate Limiting**: Respects SEC's 10 requests/second limit
- ✅ **Cache Validation**: 1-hour cache expiry with automatic refresh
- ✅ **Cache Requirement**: Prevents filtering on incomplete data

## Form 4 Detailed Tracking

Track detailed insider trading activity for specific companies:

```bash
form4 AAPL                    # Show all recent AAPL insiders
form4 NVDA TSLA MSFT         # Show recent for multiple companies
form4 AAPL -r 20             # Show 20 most recent AAPL insiders
form4 TSLA -r 15 -hp         # 15 insiders, no planned transactions
form4 MSFT -d 30 -r 10       # 10 MSFT insiders from last 30 days
form4 AAPL -tp 7/21 - 7/22   # AAPL transactions between 7/21-7/22
form4 NVDA -tp 12/1 - 12/31 -r 5  # 5 NVDA insiders in December
```

**Options:**
- `-r N`: Number of recent insiders to show per company (default: 50)
- `-hp`: Hide planned (10b5-1) transactions
- `-d D`: Limit to transactions within D days (filing date filter)
- `-tp RANGE`: Limit to transactions within date range (transaction date filter)

**Date Range Formats:**
- `M/D - M/D` or `MM/DD - MM/DD` (uses current year)
- `MM/DD/YY - MM/DD/YY` (uses specified year)

## File Organization

```
sec_filings/
├── AAPL/          # Apple filings
│   ├── 10-K/
│   ├── 10-Q/
│   ├── 8-K/
│   └── 4/
├── TSLA/          # Tesla filings
└── GOOGL/         # Google filings

analysis_results/
├── AAPL/          # Apple analyses
├── TSLA/          # Tesla analyses
└── GOOGL/         # Google analyses

cache/
└── form4_filings_cache.json  # Form 4 transaction cache (gitignored)
```

## Automation

### Cron Setup
```bash
# Daily updates at 7 AM
0 7 * * * cd /path/to/project && ./multi update-all
```

### Monitor Script
```bash
# Check specific company every hour
0 * * * * cd /path/to/project && ./track TSLA --check-only
```

## Notes

- **API Keys**: See the "API Key Setup" section above for detailed instructions
- **Rate Limits**: SEC limits requests to 10/second (handled automatically with progress bar)
- **Smart Updates**: `track` only processes new content, saving time and API calls
- **Form 4 Caching**: Cache must be built before using filters (prevents incomplete results)
- **Cache Expiry**: Form 4 cache expires after 1 hour (use `--refresh` to force update)
- **Default**: If no ticker provided, defaults to NVIDIA (CIK0001045810)

## Troubleshooting

### Form 4 Cache Issues
```bash
# Error: "No cached data available for filtering"
# Solution: Build cache first
latest 50

# Error: "429 Client Error: Too Many Requests"
# Solution: Wait a few hours for rate limit to reset, then use:
latest 50 --refresh
```

### Common Issues
- **Rate Limiting**: SEC enforces 10 requests/second - the system handles this automatically
- **Cache Expiry**: Cache expires after 1 hour - use `--refresh` to force update
- **Empty Results**: Ensure cache is built before using filters
- **Network Issues**: Check internet connection and SEC website availability

## Windows Users
Add `.bat` to commands:
```batch
track.bat AAPL
multi.bat update-all
```
