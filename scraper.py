import requests
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Import CIK lookup if available
try:
    from cik_lookup import CIKLookup
    HAS_CIK_LOOKUP = True
except ImportError:
    HAS_CIK_LOOKUP = False
    print("Warning: cik_lookup.py not found. Ticker support disabled.")

# ---- Config ----
CIK = "0001045810"  # Default NVIDIA CIK (can be overridden)

# Import user agent from config module
try:
    from config import get_user_agent
    USER_AGENT = get_user_agent()
except ImportError:
    # Fallback to environment variable or default
    import os
    USER_AGENT = os.getenv('SEC_USER_AGENT', 'SEC Filing Tracker (https://github.com/your-username/sec-api)')

FORMS_TO_GRAB = ["10-K", "10-Q", "8-K", "4"]
MAX_PER_FORM = 5 # Limit per form
M = 1 # Multiplier

# Form-specific lookback periods based on filing delays
# These determine how many days back from TODAY to look for each form type
FORM_LOOKBACK_DAYS = {
    "10-K": 365*M,   
    "10-Q": 120*M,    
    "8-K": 90*M,     
    "3": 365*M,       
    "4": 90*M,        
    "5": 365*M        
}

def is_within_lookback_period(filing_date_str, form_type):
    """Check if filing date is within the form-specific lookback period from today"""
    filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")
    
    # Get lookback days for this form type (today - lookback_days)
    lookback_days = FORM_LOOKBACK_DAYS.get(form_type, 90)
    cutoff_date = datetime.now() - timedelta(days=lookback_days)
    
    return filing_date >= cutoff_date

def fetch_recent_forms(cik, forms, max_per_form):
    """Fetch SEC filings using form-specific lookback periods from today"""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {"User-Agent": USER_AGENT}
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    filings = data["filings"]["recent"]

    found = {form: [] for form in forms}
    
    # Process filings
    for form, acc, doc, date in zip(
        filings["form"],
        filings["accessionNumber"],
        filings["primaryDocument"],
        filings["filingDate"]
    ):
        if form in forms and is_within_lookback_period(date, form) and len(found[form]) < max_per_form:
            acc_no_dash = acc.replace("-", "")
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dash}/{doc}"
            found[form].append({
                "accession": acc,
                "doc_url": doc_url,
                "form": form,
                "filing_date": date
            })
        
        # Early exit if all quotas filled
        if all(len(lst) >= max_per_form for lst in found.values()):
            break
    
    return found

def fetch_by_ticker(ticker, forms=None, max_per_form=None):
    """Fetch filings for a company by ticker symbol"""
    if not HAS_CIK_LOOKUP:
        raise ImportError("cik_lookup.py required for ticker support")
    
    if forms is None:
        forms = FORMS_TO_GRAB
    if max_per_form is None:
        max_per_form = MAX_PER_FORM
    
    # Look up CIK
    lookup = CIKLookup()
    company_info = lookup.get_company_info(ticker)
    
    if not company_info:
        raise ValueError(f"Ticker '{ticker}' not found")
    
    # Fetch filings
    filings = fetch_recent_forms(company_info['cik'], forms, max_per_form)
    
    return {
        "company": company_info,
        "filings": filings
    }

def main():
    # Check if ticker argument provided
    if len(sys.argv) > 1 and not sys.argv[1].startswith("0"):
        # Assume it's a ticker
        if not HAS_CIK_LOOKUP:
            print("Error: Ticker support requires cik_lookup.py")
            sys.exit(1)
        
        ticker = sys.argv[1].upper()
        try:
            result = fetch_by_ticker(ticker)
            company = result['company']
            filings = result['filings']
            
            # Display header
            print(f"SEC Filing Scraper - {datetime.now().strftime('%Y-%m-%d')}")
            print(f"Company: {company['name']} ({company['ticker']})")
            print(f"CIK: {company['cik']}")
            
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        # Use default CIK or provided CIK
        cik = sys.argv[1] if len(sys.argv) > 1 else CIK
        
        # Display header
        print(f"SEC Filing Scraper - {datetime.now().strftime('%Y-%m-%d')}")
        print(f"CIK: {cik}")
        
        # Fetch filings
        filings = fetch_recent_forms(cik, FORMS_TO_GRAB, MAX_PER_FORM)
    
    print("\nForm-specific lookback periods (from today):")
    for form in FORMS_TO_GRAB:
        days = FORM_LOOKBACK_DAYS.get(form, 90)
        print(f"  {form}: Last {days} days")
    print("-" * 60)
    
    # Display results
    total_found = sum(len(docs) for docs in filings.values())
    print(f"\nTotal filings found: {total_found}")
    
    for form, docs in filings.items():
        lookback = FORM_LOOKBACK_DAYS.get(form, 90)
        print(f"\n=== {form} filings ({len(docs)} found in last {lookback} days) ===")
        if not docs:
            print("None found within lookback period.")
        else:
            for i, f in enumerate(docs, 1):
                days_ago = (datetime.now() - datetime.strptime(f['filing_date'], "%Y-%m-%d")).days
                print(f"\n{i}. Filing Date: {f['filing_date']} ({days_ago} days ago)")
                print(f"   Accession: {f['accession']}")
                print(f"   URL: {f['doc_url']}")

if __name__ == "__main__":
    main()