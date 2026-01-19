import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
import requests
import time
import subprocess
from typing import Dict, List, Set, Optional
import sys
import re

# Configuration
DOWNLOAD_DIR = "sec_filings"
STATE_FILE = "filing_state.json"
ANALYSIS_STATE_FILE = "analysis_state.json"

# Import CIK lookup if available
try:
    from utils.cik import CIKLookup
    HAS_CIK_LOOKUP = True
except ImportError:
    HAS_CIK_LOOKUP = False

class FilingTracker:
    """Tracks SEC filings and their processing state"""
    
    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = Path(state_file)
        self.state = self.load_state()
        
    def load_state(self) -> Dict:
        """Load tracking state from file"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            "last_check": None,
            "filings": {},  # accession -> filing metadata
            "analyzed": {},  # form_type -> last_analysis_timestamp
            "companies": {}  # ticker/cik -> company info
        }
    
    def save_state(self):
        """Save tracking state to file"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def is_new_filing(self, accession: str) -> bool:
        """Check if a filing is new"""
        return accession not in self.state["filings"]
    
    def mark_filing_downloaded(self, filing: Dict):
        """Mark a filing as downloaded"""
        self.state["filings"][filing["accession"]] = {
            "form": filing["form"],
            "filing_date": filing["filing_date"],
            "downloaded_at": datetime.now().isoformat(),
            "doc_url": filing["doc_url"]
        }
        self.save_state()
    
    def get_new_filings(self, fetched_filings: Dict) -> Dict:
        """Filter to only new filings"""
        new_filings = {}
        for form, docs in fetched_filings.items():
            new_docs = [doc for doc in docs if self.is_new_filing(doc["accession"])]
            if new_docs:
                new_filings[form] = new_docs
        return new_filings
    
    def update_last_check(self):
        """Update the last check timestamp"""
        self.state["last_check"] = datetime.now().isoformat()
        self.save_state()
    
    def needs_analysis(self, form_type: str, force: bool = False) -> bool:
        """Check if a form type needs re-analysis"""
        if force:
            return True
            
        # Check if we have new filings for this form type
        form_filings = [f for f in self.state["filings"].values() if f["form"] == form_type]
        if not form_filings:
            return False
            
        # Check if we've analyzed this form type before
        last_analysis = self.state["analyzed"].get(form_type)
        if not last_analysis:
            return True
            
        # Check if any filings are newer than last analysis
        last_analysis_time = datetime.fromisoformat(last_analysis)
        for filing in form_filings:
            download_time = datetime.fromisoformat(filing["downloaded_at"])
            if download_time > last_analysis_time:
                return True
                
        return False
    
    def mark_analyzed(self, form_type: str):
        """Mark a form type as analyzed"""
        self.state["analyzed"][form_type] = datetime.now().isoformat()
        self.save_state()
    
    def add_company(self, ticker_or_cik: str, company_info: Optional[Dict] = None):
        """Add a company to track"""
        if "companies" not in self.state:
            self.state["companies"] = {}
        
        self.state["companies"][ticker_or_cik] = company_info or {"added": datetime.now().isoformat()}
        self.save_state()
    
    def get_most_recent_filing_date(self) -> Optional[str]:
        """Get the most recent filing date from the cache (ISO format)"""
        if not self.state["filings"]:
            return None
        
        most_recent_date = None
        for filing in self.state["filings"].values():
            filing_date = filing["filing_date"]
            if most_recent_date is None or filing_date > most_recent_date:
                most_recent_date = filing_date
        
        return most_recent_date


# Enhanced download function
def download_new_filings(tracker: FilingTracker, ticker_or_cik: Optional[str] = None):
    """Download only new filings for specified company or default"""
    from core.scraper import fetch_recent_forms, fetch_by_ticker, CIK, FORMS_TO_GRAB, MAX_PER_FORM, USER_AGENT
    
    Path(DOWNLOAD_DIR).mkdir(exist_ok=True)
    headers = {"User-Agent": USER_AGENT}
    
    # Determine what to download
    if ticker_or_cik:
        # Check if it's a ticker
        is_ticker = not ticker_or_cik.startswith("0") and HAS_CIK_LOOKUP
        
        if is_ticker:
            try:
                result = fetch_by_ticker(ticker_or_cik)
                company_info = result['company']
                all_filings = result['filings']
                company_id = company_info['ticker']
                company_name = company_info['name']
                
                # Track this company
                tracker.add_company(company_id, company_info)
                
                print(f"Checking {company_name} ({company_id}) for new filings...")
            except ValueError as e:
                print(f"Error: {e}")
                return False
        else:
            # Use CIK
            cik = ticker_or_cik
            all_filings = fetch_recent_forms(cik, FORMS_TO_GRAB, MAX_PER_FORM)
            company_id = f"CIK{cik}"
            company_name = company_id
            
            print(f"Checking {company_id} for new filings...")
    else:
        # Use default CIK
        cik = CIK
        all_filings = fetch_recent_forms(cik, FORMS_TO_GRAB, MAX_PER_FORM)
        company_id = f"CIK{cik}"
        company_name = "NVIDIA"  # Default
        
        print("Checking for new filings...")
    
    # Get the most recent filing date to optimize fetching
    most_recent_filing_date = tracker.get_most_recent_filing_date()
    if most_recent_filing_date:
        # Check if the cache might be outdated
        last_check_date = tracker.state.get("last_check")
        if last_check_date:
            days_since_check = (datetime.now() - datetime.fromisoformat(last_check_date)).days
            if days_since_check > 1:
                print(f"✓ Retrieving only filings after {most_recent_filing_date} to avoid re-caching...")
                # Re-fetch only newer filings
                if ticker_or_cik:
                    # Check if it's a ticker
                    is_ticker = not ticker_or_cik.startswith("0") and HAS_CIK_LOOKUP
                    
                    if is_ticker:
                        result = fetch_by_ticker(ticker_or_cik, from_date=most_recent_filing_date)
                        all_filings = result['filings']
                    else:
                        all_filings = fetch_recent_forms(ticker_or_cik, FORMS_TO_GRAB, MAX_PER_FORM, most_recent_filing_date)
                else:
                    all_filings = fetch_recent_forms(CIK, FORMS_TO_GRAB, MAX_PER_FORM, most_recent_filing_date)
    
    # Get only new filings
    new_filings = tracker.get_new_filings(all_filings)
    
    total_new = sum(len(docs) for docs in new_filings.values())
    if total_new == 0:
        print("✓ No new filings found.")
        return False
    
    print(f"Found {total_new} new filings to download.")
    
    # Create company directory
    company_dir = Path(DOWNLOAD_DIR) / company_id
    company_dir.mkdir(exist_ok=True)
    
    for form, docs in new_filings.items():
        if not docs:
            continue
            
        form_dir = company_dir / form
        form_dir.mkdir(exist_ok=True)
        
        print(f"\nDownloading {len(docs)} new {form} filings...")
        
        for doc in docs:
            filename = f"{doc['accession']}.html"
            file_path = form_dir / filename
            
            try:
                response = requests.get(doc['doc_url'], headers=headers)
                response.raise_for_status()
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"  ✓ Downloaded: {filename}")
                tracker.mark_filing_downloaded(doc)
                time.sleep(0.1)
                
            except Exception as e:
                print(f"  ✗ Failed: {filename} - {e}")
    
    tracker.update_last_check()
    return True


# Main orchestrator script
def main():
    """Main script to check for updates and process new filings"""
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check API keys on startup
    try:
        from utils.api_keys import ensure_sec_user_agent
        ensure_sec_user_agent()
    except ImportError:
        pass  # Continue without API key checking if utils not available
    
    import argparse
    
    parser = argparse.ArgumentParser(description='SEC Filing Update Checker')
    parser.add_argument('ticker_or_cik', nargs='?', 
                       help='Ticker symbol or CIK to process')
    parser.add_argument('--force-download', action='store_true', 
                       help='Force download all filings (ignore cache)')
    parser.add_argument('--force-analysis', action='store_true',
                       help='Force re-analysis of all forms')
    parser.add_argument('--forms', nargs='+', 
                       help='Specific forms to process (e.g., 10-K 8-K)')
    parser.add_argument('--check-only', action='store_true',
                       help='Only check for updates without downloading')
    parser.add_argument('--list-companies', action='store_true',
                       help='List tracked companies')
    args = parser.parse_args()
    
    # Initialize tracker
    tracker = FilingTracker()
    
    # List companies command
    if args.list_companies:
        if "companies" in tracker.state and tracker.state["companies"]:
            print("Tracked companies:")
            for company_id, info in tracker.state["companies"].items():
                print(f"  - {company_id}: {info}")
        else:
            print("No companies being tracked.")
        return
    
    # Show last check time
    if tracker.state["last_check"]:
        last_check = datetime.fromisoformat(tracker.state["last_check"])
        print(f"Last check: {last_check.strftime('%Y-%m-%d %H:%M:%S')}")
        hours_ago = (datetime.now() - last_check).total_seconds() / 3600
        print(f"({hours_ago:.1f} hours ago)\n")
    
    # Check for updates
    if args.force_download:
        print("Force download mode - clearing cache...")
        tracker.state["filings"] = {}
        tracker.save_state()
    
    if args.check_only:
        from core.scraper import fetch_recent_forms, fetch_by_ticker, CIK, FORMS_TO_GRAB, MAX_PER_FORM
        
        if args.ticker_or_cik:
            # Check specific company
            if not args.ticker_or_cik.startswith("0") and HAS_CIK_LOOKUP:
                try:
                    result = fetch_by_ticker(args.ticker_or_cik)
                    all_filings = result['filings']
                    company_name = result['company']['name']
                    print(f"Checking {company_name}...")
                except ValueError as e:
                    print(f"Error: {e}")
                    return
            else:
                all_filings = fetch_recent_forms(args.ticker_or_cik, FORMS_TO_GRAB, MAX_PER_FORM)
        else:
            all_filings = fetch_recent_forms(CIK, FORMS_TO_GRAB, MAX_PER_FORM)
        
        new_filings = tracker.get_new_filings(all_filings)
        
        print("Update check results:")
        for form, docs in new_filings.items():
            if docs:
                print(f"  {form}: {len(docs)} new filings")
        
        if not any(docs for docs in new_filings.values()):
            print("  No new filings found.")
        return
    
    # Download new filings
    has_new_filings = download_new_filings(tracker, args.ticker_or_cik)
    
    # Determine which forms need analysis
    from core.scraper import FORMS_TO_GRAB
    forms_to_analyze = args.forms if args.forms else FORMS_TO_GRAB
    
    forms_needing_analysis = []
    for form in forms_to_analyze:
        if tracker.needs_analysis(form, force=args.force_analysis):
            forms_needing_analysis.append(form)
    
    # Check if we should analyze even if forms are up to date
    # This happens when there are no existing analysis results
    if not forms_needing_analysis and forms_to_analyze:
        # Determine company directory for checking existing analysis
        if args.ticker_or_cik:
            if not args.ticker_or_cik.startswith("0") and HAS_CIK_LOOKUP:
                company_id = args.ticker_or_cik.upper()
            else:
                company_id = f"CIK{args.ticker_or_cik}"
        else:
            company_id = "CIK0001045810"  # Default NVIDIA
        
        # Check if analysis results exist
        analysis_dir = Path("analysis_results") / company_id
        analysis_exists = False
        if analysis_dir.exists():
            # Look for any analysis files
            for form in forms_to_analyze:
                pattern = f"{company_id}_{form}_analysis_*.txt"
                if list(analysis_dir.glob(pattern)):
                    analysis_exists = True
                    break
        
        # If no analysis exists, add all forms to analysis list
        if not analysis_exists:
            forms_needing_analysis = forms_to_analyze.copy()
            print("\nNo existing analysis found. Running analysis for all forms.")
    
    if not forms_needing_analysis:
        print("\n✓ All forms are up to date. No analysis needed.")
        return
    
    # Run analysis for forms that need it
    print(f"\nRunning analysis for: {', '.join(forms_needing_analysis)}")
    
    # Create a temporary config file for deepseek with only needed forms
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "forms_to_analyze": forms_needing_analysis,
            "tracker_state_file": str(tracker.state_file)
        }
        if args.ticker_or_cik:
            config["ticker"] = args.ticker_or_cik
        json.dump(config, f)
        config_file = f.name
    
    try:
        # Build command
        cmd = ["python", "filing_analyzer.py", "--config", config_file]
        if args.ticker_or_cik:
            cmd.append(args.ticker_or_cik)
        
        # Run the analysis script with config
        subprocess.run(cmd)
        
        # Mark forms as analyzed
        for form in forms_needing_analysis:
            tracker.mark_analyzed(form)
            
    finally:
        Path(config_file).unlink()
    
    print("\n✅ Update check complete.")
    
    # Generate summary if analysis was performed
    if forms_needing_analysis and not args.check_only:
        generate_analysis_summary(args.ticker_or_cik, forms_needing_analysis)


def extract_sentiment_from_text(text: str, form_type: str) -> Dict:
    """Extract sentiment and key info from analysis text"""
    # Sentiment keywords
    bullish_keywords = ["growth", "increase", "positive", "strong", "improved", "exceeded", "record", 
                       "momentum", "expansion", "optimistic", "buy", "acquired", "revenue growth"]
    bearish_keywords = ["decline", "decrease", "negative", "weak", "concern", "risk", "loss", 
                       "reduced", "challenging", "uncertainty", "sell", "disposed", "revenue decline"]
    
    # Count sentiment indicators
    text_lower = text.lower()
    bullish_count = sum(1 for word in bullish_keywords if word in text_lower)
    bearish_count = sum(1 for word in bearish_keywords if word in text_lower)
    
    # Determine sentiment
    if bullish_count > bearish_count * 1.5:
        sentiment = "Bullish"
    elif bearish_count > bullish_count * 1.5:
        sentiment = "Bearish"
    else:
        sentiment = "Neutral"
    
    # Extract key dates
    date_pattern = r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b|\b\d{1,2}/\d{1,2}/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b'
    dates = re.findall(date_pattern, text)[:3]  # Get first 3 dates
    
    # Extract key metrics based on form type
    key_info = []
    
    if form_type == "10-K":
        # Annual report - look for revenue, earnings
        revenue_match = re.search(r'revenue[s]?.*?(\$[\d.,]+\s*(billion|million))', text_lower)
        if revenue_match:
            key_info.append(f"Revenue: {revenue_match.group(1)}")
    
    elif form_type == "10-Q":
        # Quarterly - look for quarterly changes
        quarter_match = re.search(r'(Q[1-4]|quarter[ly]?).*?(increase|decrease|growth).*?(\d+%)', text_lower)
        if quarter_match:
            key_info.append(f"Quarterly {quarter_match.group(2)}: {quarter_match.group(3)}")
    
    elif form_type == "8-K":
        # Current report - look for events
        if "acquisition" in text_lower:
            key_info.append("Acquisition activity")
        if "appointment" in text_lower or "resigned" in text_lower:
            key_info.append("Management changes")
        if "dividend" in text_lower:
            key_info.append("Dividend announcement")
    
    elif form_type == "4":
        # Insider trading - look for buy/sell
        if "buy" in text_lower or "acquired" in text_lower:
            key_info.append("Insider buying")
        if "sell" in text_lower or "disposed" in text_lower:
            key_info.append("Insider selling")
    
    # Extract a key highlight (first significant sentence after summary/analysis markers)
    highlight_match = re.search(r'(summary|analysis|overall).*?[.!?]\s*(.+?[.!?])', text_lower, re.IGNORECASE)
    highlight = ""
    if highlight_match:
        highlight = highlight_match.group(2).strip()[:100] + "..."
    
    return {
        "sentiment": sentiment,
        "dates": dates[:2],  # Max 2 dates
        "key_info": key_info[:2],  # Max 2 key points
        "highlight": highlight
    }


def generate_analysis_summary(ticker_or_cik: str, forms_analyzed: List[str]):
    """Generate and display summary from analysis files"""
    # Determine company directory
    if ticker_or_cik:
        if not ticker_or_cik.startswith("0") and HAS_CIK_LOOKUP:
            company_id = ticker_or_cik.upper()
        else:
            company_id = f"CIK{ticker_or_cik}"
    else:
        company_id = "CIK0001045810"
    
    analysis_dir = Path("analysis_results") / company_id
    
    if not analysis_dir.exists():
        return
    
    # Find most recent analysis files
    summaries = {}
    overall_sentiment_scores = {"Bullish": 0, "Bearish": 0, "Neutral": 0}
    
    for form in forms_analyzed:
        # Find latest analysis file for this form
        pattern = f"{company_id}_{form}_analysis_*.txt"
        files = sorted(analysis_dir.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if files:
            latest_file = files[0]
            try:
                with open(latest_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract sentiment and key info
                analysis = extract_sentiment_from_text(content, form)
                summaries[form] = analysis
                overall_sentiment_scores[analysis["sentiment"]] += 1
                
            except Exception as e:
                print(f"Error reading {form} analysis: {e}")
    
    if not summaries:
        return
    
    # Determine overall sentiment
    if overall_sentiment_scores["Bullish"] > overall_sentiment_scores["Bearish"]:
        overall_sentiment = "BULLISH"
        emoji = "📈"
    elif overall_sentiment_scores["Bearish"] > overall_sentiment_scores["Bullish"]:
        overall_sentiment = "BEARISH"
        emoji = "📉"
    else:
        overall_sentiment = "NEUTRAL"
        emoji = "📊"
    
    # Display summary
    print(f"\n{'='*60}")
    print(f"📋 ANALYSIS SUMMARY - {company_id}")
    print(f"{'='*60}")
    
    print(f"\n{emoji} Overall Sentiment: {overall_sentiment}")
    print(f"   Forms analyzed: {', '.join(forms_analyzed)}")
    
    # Display each form's summary
    for form in ["10-K", "10-Q", "8-K", "4"]:
        if form in summaries:
            summary = summaries[form]
            print(f"\n📄 {form} - {summary['sentiment']}")
            
            if summary['dates']:
                print(f"   📅 Key dates: {', '.join(summary['dates'][:2])}")
            
            if summary['key_info']:
                for info in summary['key_info']:
                    print(f"   • {info}")
            
            if summary['highlight'] and len(summary['highlight']) > 10:
                print(f"   💡 {summary['highlight']}")
    
    # Key takeaways
    print(f"\n🎯 Key Takeaways:")
    
    # Bullish indicators
    bullish_forms = [f for f, s in summaries.items() if s['sentiment'] == 'Bullish']
    if bullish_forms:
        print(f"   ✅ Positive signals in: {', '.join(bullish_forms)}")
    
    # Bearish indicators
    bearish_forms = [f for f, s in summaries.items() if s['sentiment'] == 'Bearish']
    if bearish_forms:
        print(f"   ⚠️  Concerns in: {', '.join(bearish_forms)}")
    
    # Recent activity
    all_dates = []
    for summary in summaries.values():
        all_dates.extend(summary['dates'])
    if all_dates:
        print(f"   📅 Recent activity: {all_dates[0]}")
    
    print(f"\n{'='*60}")


# Utility functions for other scripts
def get_filing_metadata(accession: str) -> Optional[Dict]:
    """Get metadata for a specific filing"""
    tracker = FilingTracker()
    return tracker.state["filings"].get(accession)


def get_filings_since(date: datetime, form_type: Optional[str] = None) -> List[Dict]:
    """Get all filings since a specific date"""
    tracker = FilingTracker()
    filings = []
    
    for accession, metadata in tracker.state["filings"].items():
        filing_date = datetime.strptime(metadata["filing_date"], "%Y-%m-%d")
        if filing_date >= date:
            if form_type is None or metadata["form"] == form_type:
                filings.append({
                    "accession": accession,
                    **metadata
                })
    
    return sorted(filings, key=lambda x: x["filing_date"], reverse=True)


def print_summary():
    """Print a summary of tracked filings"""
    tracker = FilingTracker()
    
    print("SEC Filing Tracker Summary")
    print("=" * 50)
    
    # Show tracked companies
    if "companies" in tracker.state and tracker.state["companies"]:
        print("\nTracked companies:")
        for company_id, info in tracker.state["companies"].items():
            print(f"  - {company_id}")
    
    # Count by form type
    form_counts = {}
    for filing in tracker.state["filings"].values():
        form = filing["form"]
        form_counts[form] = form_counts.get(form, 0) + 1
    
    print("\nTotal tracked filings:")
    for form, count in sorted(form_counts.items()):
        last_analysis = tracker.state["analyzed"].get(form)
        status = ""
        if last_analysis:
            analysis_time = datetime.fromisoformat(last_analysis)
            status = f" (last analyzed: {analysis_time.strftime('%Y-%m-%d %H:%M')})"
        print(f"  {form}: {count} filings{status}")
    
    # Recent filings
    print("\nMost recent filings:")
    recent = get_filings_since(datetime.now() - timedelta(days=30))
    for filing in recent[:5]:
        print(f"  {filing['filing_date']} - {filing['form']} - {filing['accession']}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        print_summary()
    else:
        main()