import json
import os
from pathlib import Path
from openai import OpenAI
from datetime import datetime
import tiktoken
import re
from html.parser import HTMLParser
import argparse
import threading
import time
import sys

# Import CIK lookup if available
try:
    from utils.cik import CIKLookup
    HAS_CIK_LOOKUP = True
except ImportError:
    HAS_CIK_LOOKUP = False

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip_tags = {'script', 'style', 'meta', 'link'}
        self.current_tag = None
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag in ['br', 'p', 'div', 'tr']:
            self.text.append('\n')
        elif tag == 'td':
            self.text.append(' | ')
            
    def handle_data(self, data):
        if self.current_tag not in self.skip_tags:
            text = data.strip()
            if text:
                self.text.append(text)
                
    def handle_endtag(self, tag):
        if tag in ['p', 'div', 'table']:
            self.text.append('\n')
            
    def get_text(self):
        return ' '.join(self.text)

class Spinner:
    def __init__(self):
        self.spinning = False
        self.thread = None
        
    def spin(self):
        spinner_chars = "|/-\\"
        i = 0
        while self.spinning:
            sys.stdout.write(f"\r⏳ Fetching from API... (This might take a while.) {spinner_chars[i]} ")
            sys.stdout.flush()
            i = (i + 1) % len(spinner_chars)
            time.sleep(0.1)
        sys.stdout.write("\r" + " " * 50 + "\r")
        sys.stdout.flush()
    
    def start(self):
        self.spinning = True
        self.thread = threading.Thread(target=self.spin)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        self.spinning = False
        if self.thread:
            self.thread.join()

def extract_text_from_html(html_content):
    """Extract text from HTML, preserving structure"""
    parser = HTMLTextExtractor()
    parser.feed(html_content)
    text = parser.get_text()
    # Clean up excessive whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    return text

def analyze_filings_optimized(forms_to_analyze=None, config_file=None, ticker_or_cik=None):
    """Optimized analysis that only processes specified forms for any company"""
    
    # Load configuration
    if config_file and Path(config_file).exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
            forms_to_analyze = config.get("forms_to_analyze", forms_to_analyze)
            ticker_or_cik = config.get("ticker", ticker_or_cik) or config.get("cik", ticker_or_cik)
    
    # Configuration - Get model from environment or prompt user
    from utils.api_keys import get_current_model
    MODEL = get_current_model()
    print(f"Using model: {MODEL}")
    
    # Get API key from environment variable with fallback
    API_KEY = os.getenv('OPENROUTER_API_KEY')
    
    if not API_KEY:
        print("Warning: OPENROUTER_API_KEY environment variable not set. "
              "Analysis features will be disabled. "
              "See README.md for instructions on setting up your API key.")
        # Return early to avoid further processing
        return None
    
    # OpenRouter config - create custom httpx client with required headers
    import httpx
    http_client = httpx.Client(
        headers={
            "HTTP-Referer": "https://github.com/undeemed/SEC-Tracker",  # Optional: helps OpenRouter identify your app
            "X-Title": "SEC Filing Analyzer"  # Optional: shows in OpenRouter dashboard
        }
    )
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=API_KEY,
        http_client=http_client
    )
    
    # Token counter
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    
    def count_tokens(text):
        return len(encoding.encode(text))
    
    # Determine company info
    company_id = None
    company_name = None
    
    if ticker_or_cik:
        # Check if it's a ticker
        if not ticker_or_cik.startswith("0") and HAS_CIK_LOOKUP:
            lookup = CIKLookup()
            company_info = lookup.get_company_info(ticker_or_cik)
            if company_info:
                company_id = company_info['ticker']
                company_name = company_info['name']
            else:
                print(f"Ticker '{ticker_or_cik}' not found")
                return
        else:
            # It's a CIK
            company_id = f"CIK{ticker_or_cik}"
            company_name = company_id
    else:
        # Default to NVIDIA
        company_id = "CIK0001045810"
        company_name = "NVIDIA"
    
    # Create analysis directory
    analysis_dir = Path("analysis_results") / company_id
    analysis_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Import tracker to get filing metadata
    try:
        from core.tracker import FilingTracker
        tracker = FilingTracker()
        has_tracker = True
    except ImportError:
        has_tracker = False
        print("Warning: Running without tracker integration")
    
    # Process each filing type
    filings_dir = Path("sec_filings") / company_id
    
    if not filings_dir.exists():
        print(f"No filings found for {company_name}. Run download.py first.")
        return
    
    # Default to all forms if none specified
    if not forms_to_analyze:
        forms_to_analyze = ["4", "8-K", "10-K", "10-Q"]
    
    print(f"Analyzing {company_name} forms: {', '.join(forms_to_analyze)}")
    
    analysis_results = {}
    
    for form_type in forms_to_analyze:
        form_dir = filings_dir / form_type
        if not form_dir.exists() or not form_dir.is_dir():
            print(f"\nSkipping {form_type} - directory not found")
            continue
        
        print(f"\n{'='*50}")
        print(f"Processing {form_type} filings...")
        print(f"{'='*50}")
        
        # Get filing files
        filings = list(form_dir.glob("*.html"))
        
        # If we have tracker, we can be smarter about which files to process
        if has_tracker and ticker_or_cik == "0001045810":  # Only for default NVIDIA
            # Get only new filings since last analysis
            last_analysis = tracker.state["analyzed"].get(form_type)
            if last_analysis:
                last_analysis_time = datetime.fromisoformat(last_analysis)
                print(f"Last analysis: {last_analysis_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Filter to only newer filings
                new_filings = []
                for filing in filings:
                    accession = filing.stem
                    filing_metadata = tracker.state["filings"].get(accession)
                    if filing_metadata:
                        download_time = datetime.fromisoformat(filing_metadata["downloaded_at"])
                        if download_time > last_analysis_time:
                            new_filings.append(filing)
                
                if new_filings:
                    print(f"Found {len(new_filings)} new filings to analyze")
                    filings = new_filings
                else:
                    print(f"No new filings since last analysis")
                    continue
        
        # Combine all HTML files for this form type
        all_content = []
        
        for filing in filings:
            print(f"  Reading {filing.name}")
            try:
                with open(filing, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except:
                with open(filing, 'r', encoding='latin-1') as f:
                    html_content = f.read()
            
            # Extract text from HTML
            text_content = extract_text_from_html(html_content)
            
            # Add metadata if available
            metadata = ""
            if has_tracker and ticker_or_cik == "0001045810":
                accession = filing.stem
                filing_info = tracker.state["filings"].get(accession)
                if filing_info:
                    metadata = f"\nFiling Date: {filing_info['filing_date']}\n"
            
            all_content.append(f"\n{'='*50}\n{filing.name}{metadata}\n{'='*50}\n{text_content}")
        
        if not all_content:
            print(f"  No filings found for {form_type}")
            continue
        
        # Combine all content
        combined_content = '\n'.join(all_content)
        total_tokens = count_tokens(combined_content)
        
        print(f"\nTotal tokens for {form_type}: {total_tokens:,}")
        print(f"Total filings: {len(filings)}")
        
        # Check token limit and truncate if necessary
        MAX_TOKENS = 130000  # Leave some room for response
        if total_tokens > MAX_TOKENS:
            print(f"Warning: Content exceeds token limit. Truncating...")
            # Estimate characters per token and truncate
            chars_per_token = len(combined_content) / total_tokens
            max_chars = int(MAX_TOKENS * chars_per_token * 0.95)  # 95% to be safe
            combined_content = combined_content[:max_chars]
            total_tokens = count_tokens(combined_content)
            print(f"Truncated to {total_tokens:,} tokens")
        
        # Analyze all filings in one request
        print(f"\nAnalyzing {form_type} filings with OPEN ROUTER...")
        
        form_specific_focus = {
            "4": "insider trading patterns, buy/sell volumes, timing, ownership changes",
            "8-K": "material events, announcements, management changes, acquisitions",
            "10-K": "annual performance, long-term strategy, comprehensive risks, financial trends",
            "10-Q": "quarterly trends, sequential changes, near-term outlook, segment performance"
        }
        
        prompt = f"""Analyze these {company_name} {form_type} SEC filings comprehensively.

Focus on: {form_specific_focus.get(form_type, "key information")}

For each filing, extract:
- Filing date and key dates mentioned
- Financial metrics and changes
- Material events and developments
- Risks and opportunities
- Investment signals

Provide both individual filing summaries and overall {form_type} trends.

Filings:
{combined_content}"""
        
        try:
            # Start spinner for API call
            spinner = Spinner()
            spinner.start()
            
            response = client.chat.completions.create(
                extra_headers={
                    "X-Provider": "Targon,Chutes"  # Force 164K providers
                },
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            
            # Stop spinner when API call completes
            spinner.stop()
            
            # Check if response is valid
            if response is None or not hasattr(response, 'choices') or not response.choices:
                raise ValueError("Invalid response from API")
            
            choice = response.choices[0]
            if not hasattr(choice, 'message') or not hasattr(choice.message, 'content'):
                raise ValueError("Invalid response structure from API")
            
            analysis = choice.message.content
            if analysis is None:
                raise ValueError("API returned None content")
            
            # Save analysis
            filename = analysis_dir / f"{company_id}_{form_type}_analysis_{timestamp}.txt"
            with open(filename, "w") as f:
                f.write(f"{company_name} {form_type} Filing Analysis\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total filings analyzed: {len(filings)}\n")
                f.write(f"Total tokens: {total_tokens:,}\n")
                if has_tracker and ticker_or_cik == "0001045810":
                    last_analysis = tracker.state["analyzed"].get(form_type)
                    if last_analysis:
                        f.write(f"Previous analysis: {last_analysis}\n")
                f.write("="*50 + "\n\n")
                f.write(analysis)
            
            print(f"\n✓ {form_type} analysis saved to {filename}")
            
            analysis_results[form_type] = {
                "filename": str(filename),
                "filings_count": len(filings),
                "tokens": total_tokens,
                "timestamp": timestamp
            }
            
        except Exception as e:
            print(f"\n✗ Error analyzing {form_type}: {e}")
            analysis_results[form_type] = {"error": str(e)}
    
    # Save analysis summary
    summary_file = analysis_dir / f"{company_id}_analysis_summary_{timestamp}.json"
    with open(summary_file, "w") as f:
        json.dump({
            "company_id": company_id,
            "company_name": company_name,
            "timestamp": timestamp,
            "results": analysis_results
        }, f, indent=2)
    
    print(f"\n✅ Analysis complete. Results in {analysis_dir}/")
    return analysis_results


def main():
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check API keys on startup
    try:
        from utils.api_keys import ensure_openrouter_api_key
        ensure_openrouter_api_key()
    except ImportError:
        pass  # Continue without API key checking if utils not available
    
    parser = argparse.ArgumentParser(description='Analyze SEC filings with OPEN ROUTER')
    parser.add_argument('ticker_or_cik', nargs='?', 
                       help='Ticker symbol or CIK (defaults to NVIDIA)')
    parser.add_argument('--forms', nargs='+', 
                       help='Specific forms to analyze (e.g., 10-K 8-K)')
    parser.add_argument('--config', type=str,
                       help='Configuration file from tracker')
    parser.add_argument('--all', action='store_true',
                       help='Analyze all form types')
    
    args = parser.parse_args()
    
    forms = None
    if args.forms:
        forms = args.forms
    elif args.all:
        forms = ["4", "8-K", "10-K", "10-Q"]
    
    results = analyze_filings_optimized(
        forms_to_analyze=forms,
        config_file=args.config,
        ticker_or_cik=args.ticker_or_cik
    )
    
    # Handle case where analysis was skipped due to missing API key
    if results is None:
        print("Analysis skipped due to missing API key.")


if __name__ == "__main__":
    main()