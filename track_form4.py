#!/usr/bin/env python3
"""
SEC Form 4 Company-Specific Transaction Tracker
Fetches and displays recent insider trading activity for specific companies

Usage:
    python track_form4.py TICKER1 [TICKER2 ...] [-r N] [-hp] [-d D] [-tp DATE_RANGE]
    
    TICKER: Stock ticker symbol(s) (e.g., NVDA, AAPL, TSLA)
    
    Options:
        -r N       Number of recent insiders to show per company (default: all)
        -hp        Hide planned (10b5-1) transactions
        -d D       Limit to transactions within D days (default: no limit)
        -tp 'mm/dd(/yy) - mm/dd(/yy)'  Limit to transactions within date range (e.g., "7/21 - 7/22") year is optional
    
Examples:
    python track_form4.py NVDA                    # Show all recent NVDA insiders
    python track_form4.py AAPL MSFT GOOGL        # Show recent for multiple companies
    python track_form4.py AAPL -r 20             # Show 20 most recent AAPL insiders
    python track_form4.py TSLA META -r 15 -hp   # 15 insiders each, no planned
    python track_form4.py MSFT -d 30 -r 10      # 10 MSFT insiders from last 30 days
    python track_form4.py AAPL -tp 7/21 - 7/22   # AAPL transactions between 7/21-7/22
    python track_form4.py NVDA -tp 12/1 - 12/31 -r 5  # 5 NVDA insiders in Dec
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
from typing import List, Dict, Optional, Tuple
import time
import html
import sys
import json
import os

# Configuration section - Easily tweakable default values
CONFIG = {
    'recent_count': 30,        # Number of recent insiders to show per company
    'hide_planned': False,     # Whether to hide planned (10b5-1) transactions
    'days_back': None,         # Limit to transactions within N days (None = no limit)
    'date_range': None,        # Limit to transactions within date range (None = no limit)
    'buffer': 30               # Buffer for fetching filings to ensure enough unique insiders
}

class CompanyForm4Tracker:
    def __init__(self):
        self.base_url = "https://www.sec.gov/Archives/edgar/data"
        # Get user agent from config module with fallback
        try:
            from config import get_user_agent
            user_agent = get_user_agent()
        except ImportError:
            # Fallback to environment variable or default
            import os
            user_agent = os.getenv('SEC_USER_AGENT', 'SEC Filing Tracker (https://github.com/your-username/sec-api)')
        
        self.headers = {
            'User-Agent': user_agent
        }
        self.company_tickers = self._load_company_tickers()
    
    def _load_company_tickers(self) -> Dict:
        """Load company ticker cache or fetch from SEC"""
        cache_file = "company_tickers_cache.json"
        
        # Try to load cached data
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    # Convert to a more searchable format
                    ticker_map = {}
                    for item in data.values():
                        ticker = item.get('ticker', '').upper()
                        if ticker:
                            ticker_map[ticker] = {
                                'cik': str(item.get('cik_str', '')).zfill(10),
                                'name': item.get('title', '')
                            }
                    return ticker_map
            except Exception as e:
                print(f"Error loading cache: {e}")
        
        # Fallback: fetch from SEC
        try:
            print("Fetching company list from SEC...")
            response = requests.get(
                "https://www.sec.gov/files/company_tickers.json",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Save cache
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            
            # Convert to searchable format
            ticker_map = {}
            for item in data.values():
                ticker = item.get('ticker', '').upper()
                if ticker:
                    ticker_map[ticker] = {
                        'cik': str(item.get('cik_str', '')).zfill(10),
                        'name': item.get('title', '')
                    }
            
            return ticker_map
            
        except Exception as e:
            print(f"Error fetching company data: {e}")
            return {}
    
    def lookup_ticker(self, ticker: str) -> Optional[Tuple[str, str]]:
        """Look up CIK and company name by ticker"""
        ticker = ticker.upper()
        if ticker in self.company_tickers:
            info = self.company_tickers[ticker]
            return info['cik'], info['name']
        return None, None
    
    def get_company_form4_filings(self, cik: str, days_back: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Get Form 4 filings for a specific company"""
        filings = []
        
        # Ensure CIK is 10 digits with leading zeros
        cik_padded = cik.zfill(10)
        
        # Use CIK-specific submissions endpoint
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        
        try:
            response = requests.get(submissions_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Get recent filings
            recent_filings = data.get('filings', {}).get('recent', {})
            
            # Get filing dates, forms, and accession numbers
            forms = recent_filings.get('form', [])
            dates = recent_filings.get('filingDate', [])
            accessions = recent_filings.get('accessionNumber', [])
            
            # Only apply date filter if days_back is specified
            cutoff_date = None
            if days_back is not None:
                cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # Stop after finding enough Form 4s
            for i in range(min(len(forms), len(dates), len(accessions))):
                if forms[i] == '4':
                    try:
                        filing_date = datetime.strptime(dates[i], '%Y-%m-%d')
                        
                        # Include if no date filter or within date range
                        if cutoff_date is None or filing_date >= cutoff_date:
                            # Construct filing URL
                            cik_no_zeros = cik.lstrip('0')
                            accession_clean = accessions[i].replace('-', '')
                            filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{accession_clean}/{accessions[i]}-index.htm"
                            
                            filings.append({
                                'url': filing_url,
                                'date': filing_date,
                                'accession': accessions[i]
                            })
                            
                            # Stop if we have enough
                            if len(filings) >= limit:
                                break
                    except:
                        continue
            
        except Exception:
            pass
        
        return filings
    
    def parse_form4_xml(self, filing_url: str, company_name: str, ticker: str) -> List[Dict]:
        """Parse Form 4 XML to extract transaction details"""
        try:
            # Get the filing index page
            response = requests.get(filing_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Unescape HTML entities
            content = html.unescape(response.text)
            
            # Find the primary XML document link
            xml_link = None
            all_links = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>', content, re.IGNORECASE)
            xml_links = [(href, text) for href, text in all_links if '.xml' in href.lower()]
            
            # Look for raw XML files (not XSL transformed)
            for href, text in xml_links:
                # Skip XSL transformed files
                if 'xslF345' in href or '/xsl' in href.lower():
                    continue
                
                # Look for doc4.xml or similar
                if any(name in href.lower() for name in ['doc4.xml', 'form4.xml', 'primary_doc.xml']) or \
                   (href.endswith('.xml') and 'xsl' not in href.lower()):
                    if href.startswith('/'):
                        xml_link = "https://www.sec.gov" + href
                    elif not href.startswith('http'):
                        base_url = '/'.join(filing_url.split('/')[:-1])
                        xml_link = base_url + '/' + href
                    else:
                        xml_link = href
                    break
            
            if not xml_link:
                return []
            
            # Fetch and parse XML
            xml_response = requests.get(xml_link, headers=self.headers, timeout=10)
            xml_response.raise_for_status()
            
            xml_content = xml_response.text
            xml_content = re.sub(r'<\?xml[^>]*\?>\s*<\?xml[^>]*\?>', '<?xml version="1.0"?>', xml_content)
            xml_content = xml_content.replace('&nbsp;', ' ')
            
            try:
                root = ET.fromstring(xml_content.encode('utf-8'))
            except ET.ParseError:
                try:
                    root = ET.fromstring(xml_content)
                except:
                    return []
            
            # Extract reporting owner info
            owner_name = ""
            relationship = ""
            owner = root.find('.//reportingOwner')
            if owner is not None:
                # Get owner name
                owner_id = owner.find('.//reportingOwnerId')
                if owner_id is not None:
                    name_elem = owner_id.find('.//rptOwnerName')
                    if name_elem is not None and name_elem.text:
                        owner_name = name_elem.text.strip()
                
                # Get relationship
                rel = owner.find('.//reportingOwnerRelationship')
                if rel is not None:
                    if rel.find('.//isDirector') is not None and rel.find('.//isDirector').text == '1':
                        relationship = "Director"
                    elif rel.find('.//isOfficer') is not None and rel.find('.//isOfficer').text == '1':
                        officer_title = rel.find('.//officerTitle')
                        relationship = officer_title.text if officer_title is not None and officer_title.text else "Officer"
                    elif rel.find('.//isTenPercentOwner') is not None and rel.find('.//isTenPercentOwner').text == '1':
                        relationship = "10% Owner"
                    else:
                        relationship = "Other"
            
            # Extract transactions - try both nonDerivativeTransaction and derivativeTransaction
            transactions = []
            
            # Debug: Check what elements exist
            non_deriv_count = len(root.findall('.//nonDerivativeTransaction'))
            deriv_count = len(root.findall('.//derivativeTransaction'))
            
            if non_deriv_count == 0 and deriv_count == 0:
                # Try different path patterns
                non_deriv_count = len(root.findall('.//{*}nonDerivativeTransaction'))
                deriv_count = len(root.findall('.//{*}derivativeTransaction'))
            
            
            # Non-derivative transactions (common stock)
            for trans in root.findall('.//{*}nonDerivativeTransaction'):
                trans_data = self._parse_transaction(trans, ticker, relationship, company_name, owner_name)
                if trans_data:
                    transactions.append(trans_data)
            
            # Also check derivative transactions (options, etc.)
            for trans in root.findall('.//{*}derivativeTransaction'):
                trans_data = self._parse_derivative_transaction(trans, ticker, relationship, company_name, owner_name)
                if trans_data:
                    transactions.append(trans_data)
            
            return transactions
            
        except Exception as e:
            # Print error for debugging
            print(f"Error parsing {filing_url}: {e}")
            return []
    
    def _parse_transaction(self, trans_elem: ET.Element, ticker: str, relationship: str, 
                          company_name: str, owner_name: str) -> Optional[Dict]:
        """Parse individual transaction element"""
        try:
            # Transaction date
            trans_date_elem = trans_elem.find('.//transactionDate/value')
            trans_date = trans_date_elem.text if trans_date_elem is not None else ""
            
            trans_datetime = datetime.strptime(trans_date, "%Y-%m-%d") if trans_date else datetime.now()
            
            # Transaction type
            trans_code_elem = trans_elem.find('.//transactionCoding/transactionCode')
            trans_code = trans_code_elem.text if trans_code_elem is not None else ""
            trans_type = "buy" if trans_code in ["A", "P"] else "sell"
            
            # Check if planned
            planned = False
            footnote_refs = trans_elem.findall('.//footnoteId')
            if footnote_refs:
                planned = True
            
            form_type_elem = trans_elem.find('.//transactionCoding/transactionFormType')
            if form_type_elem is not None and form_type_elem.text == "5":
                planned = True
            
            # Shares
            shares_elem = trans_elem.find('.//transactionAmounts/transactionShares/value')
            shares = float(shares_elem.text) if shares_elem is not None and shares_elem.text else 0
            
            # Price
            price_elem = trans_elem.find('.//transactionAmounts/transactionPricePerShare/value')
            price = float(price_elem.text) if price_elem is not None and price_elem.text else 0
            
            # Dollar amount
            dollar_amount = shares * price
            
            return {
                'date': trans_date,
                'datetime': trans_datetime,
                'ticker': ticker,
                'company_name': company_name,
                'owner_name': owner_name,
                'price': price,
                'type': trans_type,
                'planned': planned,
                'shares': shares,
                'amount': dollar_amount,
                'role': relationship
            }
            
        except Exception:
            return None
    
    def _parse_derivative_transaction(self, trans_elem: ET.Element, ticker: str, relationship: str, 
                                    company_name: str, owner_name: str) -> Optional[Dict]:
        """Parse derivative transaction element (options, etc.)"""
        try:
            # Transaction date
            trans_date_elem = trans_elem.find('.//transactionDate/value')
            trans_date = trans_date_elem.text if trans_date_elem is not None else ""
            
            trans_datetime = datetime.strptime(trans_date, "%Y-%m-%d") if trans_date else datetime.now()
            
            # Transaction type
            trans_code_elem = trans_elem.find('.//transactionCoding/transactionCode')
            trans_code = trans_code_elem.text if trans_code_elem is not None else ""
            trans_type = "buy" if trans_code in ["A", "P", "M"] else "sell"
            
            # For derivatives, get underlying shares
            underlying_elem = trans_elem.find('.//underlyingSecurity')
            shares = 0
            if underlying_elem is not None:
                shares_elem = underlying_elem.find('.//underlyingSecurityShares/value')
                shares = float(shares_elem.text) if shares_elem is not None and shares_elem.text else 0
            
            # Get exercise price if available
            price_elem = trans_elem.find('.//conversionOrExercisePrice/value')
            price = float(price_elem.text) if price_elem is not None and price_elem.text else 0
            
            # If no exercise price, use transaction price
            if price == 0:
                trans_price_elem = trans_elem.find('.//transactionAmounts/transactionPricePerShare/value')
                price = float(trans_price_elem.text) if trans_price_elem is not None and trans_price_elem.text else 0
            
            # Dollar amount
            dollar_amount = shares * price if price > 0 else 0
            
            # Skip if no meaningful data
            if shares == 0 and dollar_amount == 0:
                return None
            
            return {
                'date': trans_date,
                'datetime': trans_datetime,
                'ticker': ticker,
                'company_name': company_name,
                'owner_name': owner_name,
                'price': price,
                'type': trans_type,
                'planned': False,  # Derivatives are usually not 10b5-1
                'shares': shares,
                'amount': dollar_amount,
                'role': relationship
            }
            
        except Exception:
            return None
    
    def abbreviate_role(self, role: str) -> str:
        """Abbreviate common role titles"""
        role_map = {
            'Chief Financial Officer': 'CFO',
            'Chief Executive Officer': 'CEO',
            'Chief Operating Officer': 'COO',
            'Chief Technology Officer': 'CTO',
            'Chief Information Officer': 'CIO',
            'Chief Accounting Officer': 'CAO',
            'Chief Legal Officer': 'CLO',
            'Principal Accounting Officer': 'PAO',
            'Executive Vice President': 'EVP',
            'Senior Vice President': 'SVP',
            'Vice President': 'VP',
            'Director': 'Dir',
            '10% Owner': '10%',
            'General Counsel': 'GC',
            'President': 'Pres',
            'Secretary': 'Sec',
            'Treasurer': 'Treas',
        }
        
        for full, abbr in role_map.items():
            role = role.replace(full, abbr)
        
        role = role.rstrip(',')
        
        return role
    
    def format_amount(self, amount: float) -> str:
        """Format amounts with abbreviations"""
        if amount >= 1_000_000_000:
            return f"${amount/1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            return f"${amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.0f}K"
        else:
            return f"${amount:.0f}"
    
    def format_transaction(self, trans: Dict) -> str:
        """Format single transaction for display"""
        # Date
        date_str = trans['datetime'].strftime("%m/%d/%y")
        
        # Type and planned indicator
        type_str = "BUY " if trans['type'] == 'buy' else "SELL"
        plan_str = " P" if trans['planned'] else "  "
        
        # Shares and price
        shares_str = f"{trans['shares']:,.0f}"
        price_str = f"${trans['price']:.2f}" if trans['price'] > 0 else "  -   "
        
        # Amount
        amount_str = self.format_amount(trans['amount'])
        
        # Owner and role
        owner = trans['owner_name'][:25]
        role = self.abbreviate_role(trans['role'])[:20]
        
        return f"{date_str}  {type_str}{plan_str} {shares_str:>12}   {price_str:>8}   {amount_str:>10}  {owner:>25} {role:>20}"

def parse_date_range(date_range_str: str) -> Tuple[datetime, datetime]:
    """Parse date range string like '7/21 - 7/22' into start and end datetime objects"""
    try:
        # Split on '-' to get start and end parts
        parts = date_range_str.split('-')
        if len(parts) != 2:
            raise ValueError("Date range must be in format 'M/D - M/D' or 'MM/DD - MM/DD'")
        
        start_str = parts[0].strip()
        end_str = parts[1].strip()
        
        # Parse start date
        start_parts = start_str.split('/')
        if len(start_parts) == 2:
            # Format: M/D or MM/DD - use current year
            start_month = int(start_parts[0])
            start_day = int(start_parts[1])
            start_year = datetime.now().year
        elif len(start_parts) == 3:
            # Format: MM/DD/YY - use specified year
            start_month = int(start_parts[0])
            start_day = int(start_parts[1])
            start_year = 2000 + int(start_parts[2])  # Assume 20xx for 2-digit years
        else:
            raise ValueError("Invalid start date format")
        
        # Parse end date
        end_parts = end_str.split('/')
        if len(end_parts) == 2:
            # Format: M/D or MM/DD - use current year
            end_month = int(end_parts[0])
            end_day = int(end_parts[1])
            end_year = datetime.now().year
        elif len(end_parts) == 3:
            # Format: MM/DD/YY - use specified year
            end_month = int(end_parts[0])
            end_day = int(end_parts[1])
            end_year = 2000 + int(end_parts[2])  # Assume 20xx for 2-digit years
        else:
            raise ValueError("Invalid end date format")
        
        # Create datetime objects
        start_date = datetime(start_year, start_month, start_day)
        end_date = datetime(end_year, end_month, end_day)
        
        # Handle year boundary case (e.g., 12/28 - 1/5)
        if end_date < start_date:
            # If end date is before start date, assume it's next year
            if len(end_parts) == 2:  # Only adjust if year wasn't explicitly specified
                end_date = datetime(end_year + 1, end_month, end_day)
        
        return start_date, end_date
    except Exception as e:
        print(f"Error parsing date range '{date_range_str}': {e}")
        sys.exit(1)

def parse_args():
    """Parse command line arguments"""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    tickers = []
    recent_count = CONFIG['recent_count']  # Default to showing recent insiders
    hide_planned = CONFIG['hide_planned']
    days_back = CONFIG['days_back']  # No date limit by default
    date_range = CONFIG['date_range']  # No date range filter by default
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == '-r':
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
                i += 1
                try:
                    recent_count = int(sys.argv[i])
                except ValueError:
                    print(f"Invalid count: {sys.argv[i]}")
                    sys.exit(1)
            else:
                print("Error: -r requires a number")
                print("Example: python run.py form4 AAPL -r 20")
                sys.exit(1)
        elif arg == '-hp':
            hide_planned = True
        elif arg == '-d':
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
                i += 1
                try:
                    days_back = int(sys.argv[i])
                except ValueError:
                    print(f"Invalid days: {sys.argv[i]}")
                    sys.exit(1)
            else:
                print("Error: -d requires a number")
                print("Example: python run.py form4 AAPL -d 60")
                sys.exit(1)
        elif arg == '-tp':
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
                i += 1
                try:
                    date_range = parse_date_range(sys.argv[i])
                except Exception as e:
                    print(f"Error parsing date range: {e}")
                    sys.exit(1)
            else:
                print("Error: -tp requires a date range")
                print("Example: python run.py form4 AAPL -tp 7/21 - 7/22")
                sys.exit(1)
        elif not arg.startswith('-'):
            # This is a ticker
            tickers.append(arg.upper())
        else:
            print(f"Unknown argument: {arg}")
            print(__doc__)
            sys.exit(1)
        
        i += 1
    
    if not tickers:
        print("Error: No ticker symbols provided")
        print(__doc__)
        sys.exit(1)
    
    return tickers, recent_count, hide_planned, days_back, date_range

def process_ticker(tracker: CompanyForm4Tracker, ticker: str, recent_count: int,
                  hide_planned: bool, days_back: Optional[int], date_range: Optional[Tuple[datetime, datetime]] = None) -> Optional[List[Dict]]:
    """Process a single ticker and return transactions for N most recent insiders"""
    # Look up company
    cik, company_name = tracker.lookup_ticker(ticker)
    if not cik:
        print(f"\nError: Ticker '{ticker}' not found")
        return None
    
    # Fetch more filings to ensure we get enough unique insiders
    # Fetch at least 3x the requested count to account for multiple transactions per insider
    filings_to_fetch = max(recent_count * 3, CONFIG['buffer'])
    filings = tracker.get_company_form4_filings(cik, days_back, limit=filings_to_fetch)
    
    if not filings:
        return None
    
    all_transactions = []
    unique_insiders = set()
    
    # Parse filings until we have enough unique insiders
    total_filings = len(filings)
    for i, filing in enumerate(filings):
        time.sleep(0.1)  # Rate limiting
        
        # Show progress indicator
        print(f"\rProcessing filing {i+1} of {total_filings}...", end='', flush=True)
        
        transactions = tracker.parse_form4_xml(filing['url'], company_name, ticker)
        
        for trans in transactions:
            # Track unique insiders
            insider_key = f"{trans['owner_name']}|{trans['role']}"
            unique_insiders.add(insider_key)
            all_transactions.append(trans)
        
        # Check if we have enough unique insiders
        if hide_planned:
            # Count unique insiders with non-planned transactions
            non_planned_insiders = set()
            for trans in all_transactions:
                if not trans['planned']:
                    non_planned_insiders.add(f"{trans['owner_name']}|{trans['role']}")
            if len(non_planned_insiders) >= recent_count:
                break
        else:
            if len(unique_insiders) >= recent_count:
                break
    
    # Clear progress indicator line when done
    if total_filings > 0:
        print(f"\r{' ' * 50}\r", end='', flush=True)
    
    # Filter if needed
    if hide_planned:
        all_transactions = [t for t in all_transactions if not t['planned']]
    
    # Filter by date range if specified
    if date_range:
        start_date, end_date = date_range
        all_transactions = [t for t in all_transactions if start_date <= t['datetime'] <= end_date]
    
    return all_transactions

def group_transactions_by_person(transactions: List[Dict]) -> Dict[str, List[Dict]]:
    """Group transactions by person (owner_name + role)"""
    grouped = {}
    for trans in transactions:
        key = f"{trans['owner_name']}|{trans['role']}"
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(trans)
    return grouped

def has_planned_transactions(transactions: List[Dict]) -> bool:
    """Check if any transactions in a list are planned (10b5-1)"""
    return any(trans.get('planned', False) for trans in transactions)

def display_single_company(tracker: CompanyForm4Tracker, ticker: str, transactions: List[Dict]) -> None:
    insideW = 20
    w = 80
    """Display transactions for a single company with one net row per insider"""
    if not transactions:
        print(f"\nNo transactions found for {ticker}.")
        print("Please check:")
        print("  - Ticker spelling (e.g., AAPL, NVDA, TSLA)")
        print("  - Date range (try increasing days with -d flag)")
        print("  - Requested amount (try increasing with -r flag)")
        print("  - Try removing -hp flag to include planned transactions")
        return
    
    company_name = transactions[0]['company_name']
    
    print(f"\nForm 4 Insider Trading - {ticker} ({company_name})")
    print("=" * w)
    print(f"{'Insider':<{insideW}} {'Role':<20} {'P':<2} {'Date Range':<20} {'Net Amount':>15}")
    print("-" * w)
    
    # Group transactions by person
    grouped = group_transactions_by_person(transactions)
    
    company_total_buys = 0
    company_total_sells = 0
    
    # Sort groups by most recent transaction date (newest first)
    sorted_groups = sorted(grouped.items(), 
                          key=lambda x: max(t['datetime'] for t in x[1]), 
                          reverse=True)
    
    # Take only the requested number of most recent insiders
    recent_count = int(sys.argv[sys.argv.index('-r') + 1]) if '-r' in sys.argv else len(sorted_groups)
    sorted_groups = sorted_groups[:recent_count]
    
    for person_key, person_trans in sorted_groups:
        owner_name, role = person_key.split('|')
        
        # Sort individual's transactions by date
        person_trans.sort(key=lambda x: x['datetime'])
        
        # Calculate totals for this person
        buy_amount = sum(t['amount'] for t in person_trans if t['type'] == 'buy')
        sell_amount = sum(t['amount'] for t in person_trans if t['type'] == 'sell')
        net_amount = buy_amount - sell_amount
        
        company_total_buys += buy_amount
        company_total_sells += sell_amount
        
        # Date range
        if len(person_trans) > 1:
            date_range = f"{person_trans[0]['datetime'].strftime('%m/%d/%y')}-{person_trans[-1]['datetime'].strftime('%m/%d/%y')}"
        else:
            date_range = person_trans[0]['datetime'].strftime('%m/%d/%y')
        
        # Format net amount with color indicator
        net_str = ("+" if net_amount >= 0 else "") + tracker.format_amount(net_amount)
        
        # Abbreviate role
        role_abbr = tracker.abbreviate_role(role)
        
        # Check if any transactions are planned
        has_planned = has_planned_transactions(person_trans)
        planned_indicator = "P" if has_planned else "-"
        
        # Print insider row
        print(f"{owner_name[:insideW]:<{insideW}} {role_abbr[:20]:<20} {planned_indicator:<2} {date_range:<20} {net_str:>15}")
    
    # Company totals
    print("-" * w)
    company_net = company_total_buys - company_total_sells
    net_str = ("+" if company_net >= 0 else "") + tracker.format_amount(company_net)
    print(f"\nTOTALS: Buys: {tracker.format_amount(company_total_buys)} | "
          f"Sells: {tracker.format_amount(company_total_sells)} | Net: {net_str}")
    print(f"Showing {len(sorted_groups)} most recent insiders")

def display_multiple_companies(tracker: CompanyForm4Tracker, company_data: Dict[str, List[Dict]], tickers: List[str], processed_tickers: set) -> None:
    wsize = 82
    dwsize = 20
    """Display grouped transactions for multiple companies"""
    # Check if we have any data at all
    total_transactions = sum(len(transactions) for transactions in company_data.values())
    if total_transactions == 0:
        print("\nForm 4 Insider Trading - Multiple Companies")
        print("=" * wsize)
        print("\nNo transactions found for any companies.")
        print("Please check:")
        print("  - Ticker spelling (e.g., AAPL, NVDA, TSLA)")
        print("  - Date range (try increasing days with -d flag)")
        print("  - Requested amount (try increasing with -r flag)")
        print("  - Try removing -hp flag to include planned transactions")
        return
    
    print("\nForm 4 Insider Trading - Multiple Companies")
    print("=" * wsize)
    
    # Show results for all requested tickers
    for ticker in tickers:
        if ticker in company_data:
            transactions = company_data[ticker]
            if not transactions:
                # Still show the ticker even if no transactions
                print(f"\n{ticker} - No transactions found")
                print("-" * wsize)
                continue
                
            company_name = transactions[0]['company_name']
            print(f"\n{ticker} - {company_name}")
            print("-" * wsize)
            
            # Group by person
            grouped = group_transactions_by_person(transactions)
            
            # Display header
            print(f"{'Date Range':<{dwsize}} {'Net Amount':>10}  {'Buys':>10}  {'Sells':>10}  {'P':<2} {'Insider (Role)':>22}")
            print("-" * wsize)
            
            company_total_buys = 0
            company_total_sells = 0
            
            # Process each person's transactions
            for person_key, person_trans in grouped.items():
                owner_name, role = person_key.split('|')
                
                # Sort by date
                person_trans.sort(key=lambda x: x['datetime'])
                
                # Calculate totals
                buy_amount = sum(t['amount'] for t in person_trans if t['type'] == 'buy')
                sell_amount = sum(t['amount'] for t in person_trans if t['type'] == 'sell')
                net_amount = buy_amount - sell_amount
                
                company_total_buys += buy_amount
                company_total_sells += sell_amount
                
                # Date range
                if len(person_trans) > 1:
                    date_range = f"{person_trans[0]['datetime'].strftime('%m/%d/%y')} - {person_trans[-1]['datetime'].strftime('%m/%d/%y')}"
                else:
                    date_range = person_trans[0]['datetime'].strftime('%m/%d/%y')
                
                # Format amounts
                net_str = ("-" if net_amount < 0 else "+") + tracker.format_amount(abs(net_amount))
                buy_str = tracker.format_amount(buy_amount) if buy_amount > 0 else "-"
                sell_str = "-" + tracker.format_amount(sell_amount) if sell_amount > 0 else "-"
                
                # Abbreviate role
                role_abbr = tracker.abbreviate_role(role)
                
                # Combine name and role with consistent formatting
                # Format: "Name (Role)" with max lengths to ensure alignment
                name_part = owner_name[:18]  # Max 18 chars for name
                role_part = role_abbr[:6]    # Max 6 chars for role abbreviation
                insider_info = f"{name_part} ({role_part})"
                
                # Check if any transactions are planned
                has_planned = has_planned_transactions(person_trans)
                planned_indicator = "P" if has_planned else "-"
                
                # Ensure proper right-alignment for the insider info column
                print(f"{date_range:<{dwsize}} {net_str:>10}  {buy_str:>10}  {sell_str:>10}  {planned_indicator:<2} {insider_info:>22}")
            
            # Company totals
            print("-" * wsize)
            company_net = company_total_buys - company_total_sells
            net_str = ("-" if company_net < 0 else "+") + tracker.format_amount(abs(company_net))
            print(f"{'TOTAL':<{dwsize}} {net_str:>10}  {tracker.format_amount(company_total_buys):>10}  {'-' + tracker.format_amount(company_total_sells):>10}")
        else:
            # Ticker was processed but no transactions found
            print(f"\n{ticker} - No transactions found within specified parameters")
            print("-" * wsize)

def main():
    # Parse arguments
    tickers, recent_count, hide_planned, days_back, date_range = parse_args()
    
    tracker = CompanyForm4Tracker()
    
    # Process all tickers
    company_data = {}
    processed_tickers = set()  # Track all tickers that were processed
    for ticker in tickers:
        processed_tickers.add(ticker)  # Mark as processed regardless of results
        transactions = process_ticker(tracker, ticker, recent_count, hide_planned, days_back, date_range)
        if transactions:
            company_data[ticker] = transactions
    
    # Display results
    if len(tickers) == 1:
        # Single company - use grouped format
        if tickers[0] in company_data:
            display_single_company(tracker, tickers[0], company_data[tickers[0]])
        else:
            # Even when no transactions found, call display function to show detailed error
            display_single_company(tracker, tickers[0], [])
    else:
        # Multiple companies - use grouped format
        display_multiple_companies(tracker, company_data, tickers, processed_tickers)

if __name__ == "__main__":
    main()