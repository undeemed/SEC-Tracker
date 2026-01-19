import requests
import time
from pathlib import Path
import sys

# Import required modules
try:
    from core.scraper import fetch_recent_forms, fetch_by_ticker, CIK, FORMS_TO_GRAB, MAX_PER_FORM, USER_AGENT
    from utils.cik import CIKLookup
    HAS_CIK_LOOKUP = True
except ImportError as e:
    print(f"Import error: {e}")
    from core.scraper import fetch_recent_forms, CIK, FORMS_TO_GRAB, MAX_PER_FORM, USER_AGENT
    HAS_CIK_LOOKUP = False

DOWNLOAD_DIR = "sec_filings"

def download_company_filings(ticker_or_cik, forms=None, max_per_form=None):
    """Download filings for a company by ticker or CIK"""
    Path(DOWNLOAD_DIR).mkdir(exist_ok=True)
    
    # SECURITY: Get user agent from centralized config (no hardcoded defaults)
    try:
        from utils.config import get_user_agent
        user_agent = get_user_agent()
    except ImportError:
        from utils.common import get_user_agent
        user_agent = get_user_agent()
    
    headers = {"User-Agent": user_agent}
    
    if forms is None:
        forms = FORMS_TO_GRAB
    if max_per_form is None:
        max_per_form = MAX_PER_FORM
    
    # Determine if input is ticker or CIK
    is_ticker = not ticker_or_cik.startswith("0") and HAS_CIK_LOOKUP
    
    if is_ticker:
        # Get company info and filings by ticker
        try:
            result = fetch_by_ticker(ticker_or_cik, forms, max_per_form)
            company_info = result['company']
            filings = result['filings']
            company_name = company_info['name']
            company_id = company_info['ticker']
            print(f"Downloading filings for {company_name} ({company_id})...")
        except ValueError as e:
            print(f"Error: {e}")
            return
    else:
        # Use CIK directly
        cik = ticker_or_cik
        filings = fetch_recent_forms(cik, forms, max_per_form)
        company_id = f"CIK{cik}"
        print(f"Downloading filings for {company_id}...")
    
    # Create company directory
    company_dir = Path(DOWNLOAD_DIR) / company_id
    company_dir.mkdir(exist_ok=True)
    
    total_downloaded = 0
    
    for form, docs in filings.items():
        if not docs:
            continue
            
        form_dir = company_dir / form
        form_dir.mkdir(exist_ok=True)
        
        print(f"\nDownloading {form} filings...")
        
        for doc in docs:
            filename = f"{doc['accession']}.html"
            file_path = form_dir / filename
            
            if file_path.exists():
                print(f"  Exists: {filename}")
                continue
                
            try:
                response = requests.get(doc['doc_url'], headers=headers)
                response.raise_for_status()
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"  Done: {filename}")
                total_downloaded += 1
                time.sleep(0.1)
                
            except Exception as e:
                print(f"  Failed: {filename} - {e}")
    
    print(f"\nTotal files downloaded: {total_downloaded}")
    print(f"Files saved to: {company_dir}")

def download_all():
    """Download all filings (default behavior for backward compatibility)"""
    download_company_filings(CIK)

def main():
    """Main function with command line support"""
    # Check API keys on startup
    try:
        from utils.api_keys import ensure_sec_user_agent
        ensure_sec_user_agent()
    except ImportError:
        pass  # Continue without API key checking if utils not available
    
    if len(sys.argv) > 1:
        # Download for specific company
        ticker_or_cik = sys.argv[1]
        
        # Optional: specific forms
        forms = None
        if len(sys.argv) > 2:
            forms = sys.argv[2:]
        
        download_company_filings(ticker_or_cik, forms)
    else:
        # Default behavior - download for default CIK
        download_all()

if __name__ == "__main__":
    main()