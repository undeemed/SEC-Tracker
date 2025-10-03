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
      - Note: when using a free api key you will somtimes hit rate limit. 

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

### 3. AI Model Selection

The application supports any AI model from OpenRouter. **No model is hardcoded** - you'll be prompted to choose on first use.

#### Manage Models
```bash
# Show current model
python run.py model

# Switch model interactively
python run.py model -switch
python run.py model -s
```

#### First-Time Setup
When you first run analysis without a configured model:
```
No AI model configured.

Popular OpenRouter models:
  1. deepseek/deepseek-chat-v3.1:free
  2. x-ai/grok-4-fast:free
  3. google/gemini-2.0-flash-exp:free
  4. openai/gpt-oss-20b:free
  5. z-ai/glm-4.5-air:free

Enter number (1-5) or full model name (press Enter for #1):
```

Simply type **1-5** to quickly select, or enter any model from https://openrouter.ai/models

#### Supported Models
All OpenRouter models are supported. Popular free models:
1. **DeepSeek** - `deepseek/deepseek-chat-v3.1:free` (default)
2. **X.AI Grok** - `x-ai/grok-4-fast:free`
3. **Google Gemini** - `google/gemini-2.0-flash-exp:free`
4. **OpenAI** - `openai/gpt-oss-20b:free`
5. **GLM** - `z-ai/glm-4.5-air:free`

**Model Features:**
- ✅ No hardcoded defaults
- ✅ Quick selection with numbers (1-5)
- ✅ Settings persist in `.env`
- ✅ Switch anytime with `python run.py model -s`

#### Update API Key
If you get a "User not found" error (401):
```bash
python run.py update-key
```
Get a new key at: https://openrouter.ai/keys

### 4. Primary Usage - Track Command

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

### 5. Track Options
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
- ✅ **Permanent Cache**: Cache never expires automatically (use `--refresh` to update)
- ✅ **Cache Requirement**: Prevents filtering on incomplete data

## Form 4 Cache Systems

This application uses **two separate caching systems** for Form 4 insider trading data:

### 1. Global Form 4 Cache (`latest` command)
**Location:** `cache/form4_filings_cache.json`

**Purpose:** Intelligently caches Form 4 filings from **multiple companies** to provide:
- Overall insider trading activity rankings
- Company-level net buying/selling summaries
- Cross-company comparison and filtering

**Usage:**
```bash
latest 50 -hp              # Process 50 filings, show companies from those filings
latest 100 -min 1000000   # Process 100 filings, show companies with >$1M net activity
latest 500                # Process exactly 500 filings
```

**Smart Cache Behavior:**
- 🧠 **Intelligent Caching**: Caches filings up to the largest number requested by user
- 📊 **Count-Aware**: If cache has 500 filings and you request `latest 300`, uses cache instantly
- 🔄 **Incremental Updates**: Only fetches new filings since last transaction, merges with existing data
- 🚫 **Duplicate Prevention**: Uses accession numbers to prevent duplicate transactions
- ⚡ **Instant Results**: All filtering happens on cached data (fast response)
- 📈 **Direct Filing Mapping**: `latest X` = exactly X filings processed and displayed
- 🎯 **File-Based Display**: Shows companies found within the requested X filings only
- 🔒 **Persistent**: Cache persists until manually refreshed with `--refresh`

**Example Workflow:**
```bash
python run.py latest 500    # Cache up to 500 filings (slow first time)
python run.py latest 300    # Uses cache instantly - processes first 300 filings (fast)
python run.py latest 400    # Uses cache instantly - processes first 400 filings (fast)
python run.py latest 600    # Fetches additional filings since only 500 cached (slow)
```

### 2. Company-Specific Form 4 Cache (`form4` command)
**Location:** `cache/form4_track/{TICKER}_form4_cache.json`

**Purpose:** Deep-dives into **individual companies** to provide:
- Detailed insider-by-insider transaction breakdowns
- Individual transaction details (shares, prices, amounts)
- Insider role identification (CEO, CFO, Director, etc.)
- Company-specific analysis and filtering

**Usage:**
```bash
form4 AAPL -r 20           # 20 most recent AAPL insiders
form4 NVDA -tp 7/21-7/22  # NVDA transactions in date range
form4 TSLA -d 30 -hp       # TSLA insiders last 30 days, no planned
```

**Cache Behavior:**
- 📁 Separate file for each company (`AAPL_form4_cache.json`, `NVDA_form4_cache.json`, etc.)
- 🔍 Analyzes individual Form 4 filings per company
- 📊 Stores detailed transaction data including insider names and roles
- ⚡ Incremental updates - only fetches new filings since last cache
- 🔄 Cache builds automatically after first company lookup

### Key Distinctions

| Feature | Global Cache (`latest`) | Company Cache (`form4`) |
|---------|------------------------|------------------------|
| **Scope** | Multiple companies (X filings processed) | Individual company |
| **Data** | Company summaries from X filings | Detailed transactions |
| **File Size** | Adaptive (~50-500+ filings cached) | Per-company (~50-200 transactions) |
| **Building** | Smart (`latest X` processes exactly X filings) | Automatic (per request) |
| **Updates** | Incremental (only new filings) | Incremental (only new filings) |
| **Deduplication** | Accession numbers | Accession numbers |
| **Display Logic** | Shows companies from requested X filings only | Shows all transactions for company |
| **Filtering** | Company-level activity within X filings | Insider-level details |
| **Use Case** | Filing-based portfolio overview | Company deep-dive |

### Cache Independence & Performance
- ✅ Both caches operate **completely independently**
- ✅ Building one cache doesn't affect the other
- ✅ Each uses optimized fetching strategies for its specific use case
- ✅ Both respect SEC rate limits and avoid redundant API calls

**Performance Benefits:**
- 🚀 **80% reduction** in unnecessary API calls with smart incremental updates
- ⚡ **Instant results** for any request ≤ cached amount
- 🧠 **Intelligent scaling** - cache grows automatically as needed
- 🔄 **Smart merging** - new filings added without duplicates
- 📊 **Metadata tracking** - remembers how many filings are cached

**Clear Example:**
```bash
# After caching 500 filings:
latest 50   # Processing 50 transactions from 51 unique filings (requested: 50)
           # Total: ~37 companies, 50 transactions

latest 100  # Processing 100 transactions from 101 unique filings (requested: 100)  
           # Total: ~60 companies, 100 transactions

latest 150  # Processing 150 transactions from 151 unique filings (requested: 150)
           # Total: ~90 companies, 150 transactions
# etc...
```

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
├── form4_filings_cache.json      # Global Form 4 cache (all companies)
└── form4_track/                  # Company-specific Form 4 caches (gitignored)
    ├── AAPL_form4_cache.json    # Apple insider transactions
    ├── TSLA_form4_cache.json    # Tesla insider transactions
    └── NVDA_form4_cache.json    # NVIDIA insider transactions
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
- **Permanent Cache**: Form 4 cache never expires automatically (use `--refresh` to manually update)
- **Default**: If no ticker provided, defaults to NVIDIA (CIK0001045810)

## Troubleshooting

### API & Authentication Issues

#### "User not found" Error (401)
**Error:** `Error code: 401 - {'error': {'message': 'User not found.', 'code': 401}}`

**Cause:** Invalid or expired OpenRouter API key

**Quick Fix:**
```bash
python run.py update-key
```

**Manual Fix:**
1. Get a new API key from https://openrouter.ai/keys
2. Sign in with Google/GitHub/Discord
3. Click "Create Key" and copy it (starts with `sk-or-v1-`)
4. Update your `.env` file:
   ```bash
   nano .env
   # Update: OPENROUTER_API_KEY=sk-or-v1-your-new-key-here
   ```

**Verify API Key:**
```bash
source .env
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/auth/key
```

#### Model Not Configured
**Error:** `No AI model configured.`

**Solution:**
```bash
python run.py model -switch    # Interactive selection (pick 1-5)
python run.py model            # Show current model
```

#### Rate Limit Errors (429)
**Error:** `Error code: 429 - Rate limit exceeded`

**Solutions:**
- Wait a few minutes and try again
- Switch to a different free model: `python run.py model -switch`
- Try DeepSeek (#1) or Gemini (#3) - often have higher limits
- Check balance at https://openrouter.ai/credits

#### Model Not Found Error
**Error:** `Error: Model 'xyz' not found`

**Solution:**
1. Check model name at https://openrouter.ai/models
2. Ensure `:free` suffix for free models
3. Update: `python run.py model -switch`

---

### Cache Issues

#### Form 4 Cache Not Available
```bash
# Error: "No cached data available for filtering"
# Solution: Build cache first
latest 50

# Want to refresh cache with new data?
latest 50 --refresh
```

#### Manually Refresh Caches
All caches are permanent and never expire automatically. To refresh:

```bash
# Refresh Form 4 cache
latest 50 --refresh

# Refresh company ticker cache (delete and rebuild)
rm company_tickers_cache.json
python run.py scan AAPL
```

#### SEC Rate Limiting (429)
**Error:** `429 Client Error: Too Many Requests`

**Solution:**
- Wait a few hours for SEC rate limit to reset
- The system respects SEC's 10 requests/second limit
- Use `--refresh` cautiously to avoid hitting limits

---

### Environment & Setup Issues

#### Environment Variables Not Loading
**Symptom:** Script can't find API key even though it's in `.env`

**Solution:**
```bash
# Verify .env file exists
cat .env | grep OPENROUTER_API_KEY

# Make sure you're running from project directory
cd /Users/xiao/Documents/sec_api
python run.py analyze AAPL --forms 10-K
```

#### Dependency Issues
```bash
# Update all dependencies
pip install --upgrade openai httpx python-dotenv tiktoken requests tqdm
```

---

### Common Issues Summary
- **Rate Limiting**: SEC enforces 10 requests/second (handled automatically)
- **Stale Cache**: Cache never expires - use `--refresh` to manually update
- **Empty Results**: Build cache first before using filters
- **Network Issues**: Check internet connection and SEC website availability
- **API Errors**: Use `python run.py update-key` to fix authentication issues

---

### Quick Reference Commands

```bash
# API & Model Management
python run.py update-key         # Update OpenRouter API key
python run.py model              # Show current model
python run.py model -switch      # Switch model (pick 1-5)

# Cache Management
latest 50 --refresh              # Refresh Form 4 cache
rm company_tickers_cache.json    # Clear ticker cache

# Testing
python filing_analyzer.py AAPL --forms 8-K  # Test analysis (low cost)
python run.py                    # View all commands
```

---

### Getting Help

1. **Check API Status**: https://status.openrouter.ai/
2. **Review Logs**: Check terminal output for error codes
3. **Test API Key**: Use verification command above
4. **Check Credits**: https://openrouter.ai/credits

**Cost Info:**
- Free Tier: limit of 50 Open Router api requests
   - Deposit $10 for 1000 requests (at no extra cost if using only free models)
- Typical Cost: ~$0.001-0.01 per filing analysis (depends on filing size)
- Most free models (`:free` suffix) use no credits!

## Windows Users
Add `.bat` to commands:
```batch
track.bat AAPL
multi.bat update-all
```
