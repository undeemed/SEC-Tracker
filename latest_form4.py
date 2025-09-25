#!/usr/bin/env python3
"""
SEC Form 4 Transaction Retrieval Script
Fetches and displays recent insider trading transactions from SEC EDGAR
Groups by company and shows net insider activity trends

Usage:
    python latest_form4.py [amount] [date_range] [filters]
    
    amount: Number of results to show (default: 30)
    date_range: Date range in quotes (e.g., '7/20/25 - 7/25/25' or 'today')
    
    filters:
        -hp        Hide planned (10b5-1) transactions
        -min X     Hide companies with net activity below $X (absolute value)
        -min +X    Hide companies with total buys below $X
        -min -X    Hide companies with total sells below $X
        -m         Sort by most insider activity (transaction count)
    
Examples:
    python latest_form4.py 50                    # Show 50 results
    python latest_form4.py 30 -hp                # Hide planned transactions
    python latest_form4.py 40 -min 100000        # Only show companies with net activity >= $100K
    python latest_form4.py 25 -min +500000       # Only show companies with total buys >= $500K
    python latest_form4.py 20 -min -1000000 -hp  # Only show companies with total sells >= $1M, no planned
    python latest_form4.py today                  # Show today's transactions
    python latest_form4.py '7/20/25 - 7/25/25'   # Show transactions in date range
    python latest_form4.py today -m               # Show today's most active tickers
    python latest_form4.py '7/1 - 7/27' -m 10    # Top 10 most active in July
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
from typing import List, Dict, Optional, Tuple
import time
from collections import defaultdict
import html
import sys
from tqdm import tqdm
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path

class RateLimiter:
    """Rate limiter to ensure we don't exceed 10 requests per second"""
    def __init__(self, max_requests_per_second=10):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limit"""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()

class Form4Parser:
    def __init__(self):
        self.base_url = "https://www.sec.gov/Archives/edgar/data"
        self.rate_limiter = RateLimiter(max_requests_per_second=10)
        
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
        
        # Cache configuration
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "form4_filings_cache.json"
        self.cache_expiry_hours = 1  # Cache expires after 1 hour
    
    def parse_date_range(self, date_str: str) -> Tuple[datetime, datetime]:
        """Parse date range string into start and end datetime objects"""
        # Handle 'today' special case
        if date_str.lower() == 'today':
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            return today, tomorrow
        
        # Handle date range format: 'M/D/YY - M/D/YY' or 'M/D - M/D'
        try:
            parts = date_str.split('-')
            if len(parts) != 2:
                raise ValueError("Date range must be in format 'M/D/YY - M/D/YY' or 'M/D - M/D'")
            
            start_str = parts[0].strip()
            end_str = parts[1].strip()
            
            # Parse start date
            start_parts = start_str.split('/')
            if len(start_parts) == 2:
                # M/D format - use current year
                start_month = int(start_parts[0])
                start_day = int(start_parts[1])
                start_year = datetime.now().year
            elif len(start_parts) == 3:
                # M/D/YY format
                start_month = int(start_parts[0])
                start_day = int(start_parts[1])
                year_str = start_parts[2]
                if len(year_str) == 2:
                    start_year = 2000 + int(year_str)
                else:
                    start_year = int(year_str)
            else:
                raise ValueError("Invalid start date format")
            
            # Parse end date
            end_parts = end_str.split('/')
            if len(end_parts) == 2:
                # M/D format - use current year
                end_month = int(end_parts[0])
                end_day = int(end_parts[1])
                end_year = datetime.now().year
            elif len(end_parts) == 3:
                # M/D/YY format
                end_month = int(end_parts[0])
                end_day = int(end_parts[1])
                year_str = end_parts[2]
                if len(year_str) == 2:
                    end_year = 2000 + int(year_str)
                else:
                    end_year = int(year_str)
            else:
                raise ValueError("Invalid end date format")
            
            start_date = datetime(start_year, start_month, start_day)
            end_date = datetime(end_year, end_month, end_day, 23, 59, 59)  # End of day
            
            # Handle year boundary
            if end_date < start_date and len(end_parts) == 2:
                end_date = datetime(end_year + 1, end_month, end_day, 23, 59, 59)
            
            return start_date, end_date
            
        except Exception as e:
            raise ValueError(f"Invalid date range format: {date_str}. Use 'M/D/YY - M/D/YY' or 'today'")
    
    def is_cache_valid(self) -> bool:
        """Check if cache file exists and is not expired"""
        if not self.cache_file.exists():
            return False
        
        # Check if cache is expired
        cache_time = datetime.fromtimestamp(self.cache_file.stat().st_mtime)
        expiry_time = cache_time + timedelta(hours=self.cache_expiry_hours)
        return datetime.now() < expiry_time
    
    def get_cache_date(self) -> Optional[datetime]:
        """Get the date when cache was last updated"""
        if not self.cache_file.exists():
            return None
        
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
                if isinstance(cache_data, dict) and 'cache_date' in cache_data:
                    return datetime.fromisoformat(cache_data['cache_date'])
                elif isinstance(cache_data, list) and len(cache_data) > 0:
                    # Legacy format - use file modification time
                    return datetime.fromtimestamp(self.cache_file.stat().st_mtime)
        except (json.JSONDecodeError, FileNotFoundError, ValueError):
            pass
        
        return None
    
    def is_cache_date_current(self) -> bool:
        """Check if cache date matches today's date"""
        cache_date = self.get_cache_date()
        if cache_date is None:
            return False
        
        today = datetime.now().date()
        cache_date_only = cache_date.date()
        return cache_date_only == today
    
    def load_cache(self) -> Optional[List[Dict]]:
        """Load transaction data from cache if valid"""
        if not self.is_cache_valid():
            return None
        
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
                
                # Handle new format with cache_date
                if isinstance(cache_data, dict) and 'transactions' in cache_data:
                    transactions = cache_data['transactions']
                elif isinstance(cache_data, list):
                    # Legacy format
                    transactions = cache_data
                else:
                    return None
                
                # Convert datetime strings back to datetime objects
                for transaction in transactions:
                    if 'datetime' in transaction and isinstance(transaction['datetime'], str):
                        transaction['datetime'] = datetime.fromisoformat(transaction['datetime'])
                return transactions
        except (json.JSONDecodeError, FileNotFoundError, ValueError):
            return None
    
    def save_cache(self, transactions: List[Dict], merge_with_existing: bool = True) -> None:
        """Save transaction data to cache"""
        try:
            # Convert datetime objects to strings for JSON serialization
            cache_transactions = []
            for transaction in transactions:
                transaction_copy = transaction.copy()
                if 'datetime' in transaction_copy and isinstance(transaction_copy['datetime'], datetime):
                    transaction_copy['datetime'] = transaction_copy['datetime'].isoformat()
                cache_transactions.append(transaction_copy)
            
            # Merge with existing cache if requested
            if merge_with_existing and self.cache_file.exists():
                try:
                    with open(self.cache_file, 'r') as f:
                        existing_data = json.load(f)
                    
                    if isinstance(existing_data, dict) and 'transactions' in existing_data:
                        existing_transactions = existing_data['transactions']
                    elif isinstance(existing_data, list):
                        existing_transactions = existing_data
                    else:
                        existing_transactions = []
                    
                    # Convert existing transactions back to datetime objects for comparison
                    for trans in existing_transactions:
                        if 'datetime' in trans and isinstance(trans['datetime'], str):
                            trans['datetime'] = datetime.fromisoformat(trans['datetime'])
                    
                    # Merge transactions, avoiding duplicates based on datetime and ticker
                    existing_dict = {}
                    for trans in existing_transactions:
                        key = f"{trans.get('datetime', '')}_{trans.get('ticker', '')}_{trans.get('amount', 0)}"
                        existing_dict[key] = trans
                    
                    # Add new transactions
                    for trans in cache_transactions:
                        key = f"{trans.get('datetime', '')}_{trans.get('ticker', '')}_{trans.get('amount', 0)}"
                        if key not in existing_dict:
                            existing_dict[key] = trans
                    
                    # Convert back to list and convert datetime objects to strings
                    merged_transactions = []
                    for trans in existing_dict.values():
                        trans_copy = trans.copy()
                        if 'datetime' in trans_copy and isinstance(trans_copy['datetime'], datetime):
                            trans_copy['datetime'] = trans_copy['datetime'].isoformat()
                        merged_transactions.append(trans_copy)
                    
                    cache_transactions = merged_transactions
                    
                except (json.JSONDecodeError, FileNotFoundError, ValueError):
                    # If merge fails, just use new transactions
                    pass
            
            # Save with cache date
            cache_data = {
                'cache_date': datetime.now().isoformat(),
                'transactions': cache_transactions
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            # Silently fail cache save to avoid disrupting main functionality
            pass
    
    def get_recent_filings(self, days_back: int = 5, date_range: Optional[Tuple[datetime, datetime]] = None, use_cache: bool = True) -> List[Dict]:
        """Get recent Form 4 filings from SEC EDGAR using daily index or cache"""
        
        # Try to load from cache first if requested
        if use_cache:
            cached_filings = self.load_cache()
            if cached_filings is not None:
                return cached_filings
        
        filings = []
        
        # If date range specified, calculate days to look back
        if date_range:
            start_date, end_date = date_range
            # Calculate days back from today to start date
            days_diff = (datetime.now() - start_date).days
            days_back = max(days_back, days_diff + 2)  # Add buffer
        
        # Check multiple days of index files
        for i in range(days_back):
            date = datetime.now() - timedelta(days=i)
            # SEC only has indexes for business days
            if date.weekday() < 5:  # Monday = 0, Friday = 4
                date_str = date.strftime("%Y%m%d")
                
                # Use daily index JSON format
                index_url = f"https://www.sec.gov/Archives/edgar/daily-index/{date.year}/QTR{((date.month-1)//3)+1}/form.{date_str}.idx"
                
                try:
                    self.rate_limiter.wait_if_needed()
                    response = requests.get(index_url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        # Parse the index file
                        lines = response.text.split('\n')
                        
                        # Skip header lines
                        data_started = False
                        for line in lines:
                            if line.startswith('----'):
                                data_started = True
                                continue
                            
                            if data_started and line.strip():
                                # Index format: Form Type|Company Name|CIK|Date Filed|File Name
                                parts = line.split('|') if '|' in line else line.split()
                                
                                if len(parts) >= 5 and parts[0].strip() == '4':
                                    # This is a Form 4 filing
                                    filing_path = parts[-1].strip()
                                    filing_url = f"https://www.sec.gov/Archives/{filing_path.replace('.txt', '-index.htm')}"
                                    
                                    filings.append({
                                        'url': filing_url,
                                        'date': date,
                                        'title': f"Form 4 - {parts[1].strip() if len(parts) > 1 else 'Unknown'}"
                                    })
                except Exception as e:
                    print(f"Error fetching index for {date_str}: {e}")
                    continue
        
        # If daily index approach fails, fallback to ATOM feed
        if not filings:
            print("Daily index not available, trying ATOM feed...")
            atom_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&company=&dateb=&owner=include&start=0&count=500&output=atom"
            
            try:
                self.rate_limiter.wait_if_needed()
                response = requests.get(atom_url, headers=self.headers, timeout=10)
                response.raise_for_status()
                
                # Parse ATOM/XML feed
                ET.register_namespace('', 'http://www.w3.org/2005/Atom')
                root = ET.fromstring(response.content)
                
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                
                for entry in root.findall('atom:entry', ns):
                    title_elem = entry.find('atom:title', ns)
                    title = title_elem.text if title_elem is not None else ""
                    
                    link_elem = entry.find('atom:link[@rel="alternate"]', ns)
                    link = link_elem.get('href') if link_elem is not None else ""
                    
                    updated_elem = entry.find('atom:updated', ns)
                    updated = updated_elem.text if updated_elem is not None else ""
                    
                    try:
                        filing_date = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                        filings.append({
                            'url': link,
                            'date': filing_date,
                            'title': title
                        })
                    except:
                        continue
                        
            except Exception as e:
                print(f"Error fetching ATOM feed: {e}")
        
        return filings[:500]  # Increased limit for more companies
    
    def parse_form4_xml(self, filing_url: str) -> List[Dict]:
        """Parse Form 4 XML to extract transaction details"""
        try:
            # Get the filing index page
            self.rate_limiter.wait_if_needed()
            response = requests.get(filing_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Unescape HTML entities
            content = html.unescape(response.text)
            
            # Try to extract company name from filing page
            company_name = ""
            name_match = re.search(r'COMPANY CONFORMED NAME:\s*([^\n]+)', content)
            if name_match:
                company_name = name_match.group(1).strip()
            
            # Find the primary XML document link - look for various patterns
            xml_link = None
            for line in content.split('\n'):
                # Look for Form 4 XML files with different naming patterns
                if any(pattern in line.lower() for pattern in ['form4.xml', 'primary_doc.xml', 'doc4.xml', '.xml']):
                    match = re.search(r'href="([^"]+\.xml)"', line)
                    if match:
                        href = match.group(1)
                        # Build full URL if needed
                        if href.startswith('/'):
                            xml_link = "https://www.sec.gov" + href
                        elif not href.startswith('http'):
                            # Relative URL - construct from filing URL base
                            base_url = '/'.join(filing_url.split('/')[:-1])
                            xml_link = base_url + '/' + href
                        else:
                            xml_link = href
                        # Prefer files with 'form4' in the name
                        if 'form4' in href.lower():
                            break
            
            if not xml_link:
                return []
            
            # Fetch and parse XML
            self.rate_limiter.wait_if_needed()
            xml_response = requests.get(xml_link, headers=self.headers, timeout=10)
            xml_response.raise_for_status()
            
            # Clean up common XML issues
            xml_content = xml_response.text
            # Remove XML declaration if duplicated
            xml_content = re.sub(r'<\?xml[^>]*\?>\s*<\?xml[^>]*\?>', '<?xml version="1.0"?>', xml_content)
            # Fix common HTML entities in XML
            xml_content = xml_content.replace('&nbsp;', ' ')
            
            try:
                root = ET.fromstring(xml_content.encode('utf-8'))
            except ET.ParseError:
                # Try without encoding
                try:
                    root = ET.fromstring(xml_content)
                except:
                    return []
            
            # Extract issuer info
            issuer = root.find('.//issuer')
            ticker = ""
            issuer_name = company_name  # Use extracted name as fallback
            if issuer is not None:
                ticker_elem = issuer.find('.//issuerTradingSymbol')
                ticker = ticker_elem.text.strip() if ticker_elem is not None and ticker_elem.text else ""
                
                # Try to get issuer name from XML
                issuer_name_elem = issuer.find('.//issuerName')
                if issuer_name_elem is not None and issuer_name_elem.text:
                    issuer_name = issuer_name_elem.text.strip()
            
            # Extract reporting owner info
            owner = root.find('.//reportingOwner')
            relationship = ""
            if owner is not None:
                rel = owner.find('.//reportingOwnerRelationship')
                if rel is not None:
                    # Check various relationship fields
                    if rel.find('.//isDirector') is not None and rel.find('.//isDirector').text == '1':
                        relationship = "Director"
                    elif rel.find('.//isOfficer') is not None and rel.find('.//isOfficer').text == '1':
                        officer_title = rel.find('.//officerTitle')
                        relationship = officer_title.text if officer_title is not None else "Officer"
                    elif rel.find('.//isTenPercentOwner') is not None and rel.find('.//isTenPercentOwner').text == '1':
                        relationship = "10% Owner"
                    else:
                        relationship = "Other"
            
            # Extract transactions
            transactions = []
            for trans in root.findall('.//nonDerivativeTransaction'):
                trans_data = self._parse_transaction(trans, ticker, relationship, issuer_name)
                if trans_data:
                    transactions.append(trans_data)
            
            return transactions
            
        except Exception as e:
            # Silently skip errors to avoid cluttering output
            return []
    
    def _parse_transaction(self, trans_elem: ET.Element, ticker: str, relationship: str, company_name: str) -> Optional[Dict]:
        """Parse individual transaction element"""
        try:
            # Transaction date
            trans_date_elem = trans_elem.find('.//transactionDate/value')
            trans_date = trans_date_elem.text if trans_date_elem is not None else ""
            
            # Parse date to datetime
            trans_datetime = datetime.strptime(trans_date, "%Y-%m-%d") if trans_date else datetime.now()
            
            # Transaction type (A=Acquired, D=Disposed)
            trans_code_elem = trans_elem.find('.//transactionCoding/transactionCode')
            trans_code = trans_code_elem.text if trans_code_elem is not None else ""
            trans_type = "buy" if trans_code in ["A", "P"] else "sell"
            
            # Check if planned (10b5-1)
            planned = False
            # Check for footnote references
            footnote_refs = trans_elem.findall('.//footnoteId')
            if footnote_refs:
                planned = True  # Often footnotes indicate 10b5-1 plans
            
            # Also check transaction form type
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
                'price': price,
                'type': trans_type,
                'planned': planned,
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
        
        # Apply abbreviations
        for full, abbr in role_map.items():
            role = role.replace(full, abbr)
        
        # Remove commas from end
        role = role.rstrip(',')
        
        # Shorten long titles
        if len(role) > 30:
            role = role[:27] + '...'
            
        return role
    
    def format_amount(self, amount: float) -> str:
        """Format amounts with abbreviations (K, M, B)"""
        if amount >= 1_000_000_000:
            return f"${amount/1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            return f"${amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.0f}K"
        else:
            return f"${amount:.0f}"
    
    def group_transactions(self, all_transactions: List[Dict], hide_planned: bool = False, 
                           min_amount: Optional[float] = None, min_buy: Optional[float] = None, 
                           min_sell: Optional[float] = None, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict]:
        """Group transactions by ticker and analyze insider activity trends"""
        
        # Filter by date range if specified
        if date_range:
            start_date, end_date = date_range
            all_transactions = [t for t in all_transactions 
                               if start_date <= t['datetime'] <= end_date]
        
        # First group all transactions (with planned filter only)
        grouped: Dict[str, Dict] = defaultdict(lambda: {
            'transactions': [],
            'buy_transactions': [],
            'sell_transactions': [],
            'company_name': '',
            'latest_date': None,
            'earliest_date': None,
            'planned_count': 0,
            'total_count': 0
        })
        
        # Group by ticker, filtering only planned if requested
        for trans in all_transactions:
            # Skip planned transactions if requested
            if hide_planned and trans.get('planned', False):
                continue
            
            ticker = trans['ticker']
            grouped[ticker]['transactions'].append(trans)
            grouped[ticker]['total_count'] += 1
            
            if trans.get('company_name'):
                grouped[ticker]['company_name'] = trans['company_name']
            
            # Count planned transactions
            if trans.get('planned', False):
                grouped[ticker]['planned_count'] += 1
            
            # Separate by type
            if trans['type'] == 'buy':
                grouped[ticker]['buy_transactions'].append(trans)
            else:
                grouped[ticker]['sell_transactions'].append(trans)
            
            # Track date range
            if grouped[ticker]['latest_date'] is None or trans['datetime'] > grouped[ticker]['latest_date']:
                grouped[ticker]['latest_date'] = trans['datetime']
            if grouped[ticker]['earliest_date'] is None or trans['datetime'] < grouped[ticker]['earliest_date']:
                grouped[ticker]['earliest_date'] = trans['datetime']
        
        # Convert to list format with analysis
        result = []
        for ticker, data in grouped.items():
            if not data['transactions']:
                continue
            
            # Calculate totals
            buy_count = len(data['buy_transactions'])
            sell_count = len(data['sell_transactions'])
            buy_amount = sum(t['amount'] for t in data['buy_transactions'])
            sell_amount = sum(t['amount'] for t in data['sell_transactions'])
            buy_shares = sum(t['shares'] for t in data['buy_transactions'])
            sell_shares = sum(t['shares'] for t in data['sell_transactions'])
            
            # Calculate net activity
            net_amount = buy_amount - sell_amount
            net_shares = buy_shares - sell_shares
            
            # Apply filters on aggregated amounts
            if min_amount is not None and abs(net_amount) < min_amount:
                continue
            if min_buy is not None and buy_amount < min_buy:
                continue
            if min_sell is not None and sell_amount < min_sell:
                continue
            
            # Get unique roles
            all_roles = set()
            for t in data['transactions']:
                all_roles.add(self.abbreviate_role(t['role']))
            
            # Calculate net activity
            net_amount = buy_amount - sell_amount
            net_shares = buy_shares - sell_shares
            
            # Determine trend
            if buy_count > 0 and sell_count == 0:
                trend = "BUYING"
            elif sell_count > 0 and buy_count == 0:
                trend = "SELLING"
            elif net_amount > 0:
                trend = "NET BUY"
            elif net_amount < 0:
                trend = "NET SELL"
            else:
                trend = "NEUTRAL"
            
            # Format company name - keep reasonable length
            company_name = data['company_name'][:20] if data['company_name'] else ""
            
            # Determine if mostly planned
            is_planned = data['planned_count'] > data['total_count'] / 2
            
            summary = {
                'ticker': ticker,
                'company_name': company_name,
                'latest_date': data['latest_date'],
                'earliest_date': data['earliest_date'],
                'buy_count': buy_count,
                'sell_count': sell_count,
                'buy_amount': buy_amount,
                'sell_amount': sell_amount,
                'buy_shares': buy_shares,
                'sell_shares': sell_shares,
                'net_amount': net_amount,
                'net_shares': net_shares,
                'trend': trend,
                'roles': ', '.join(sorted(all_roles)),
                'is_planned': is_planned,
                'planned_count': data['planned_count'],
                'total_count': data['total_count']
            }
            result.append(summary)
        
        # Sort by most recent transaction date (descending)
        result.sort(key=lambda x: x['latest_date'], reverse=True)
        return result
    
    def process_filings_concurrently(self, filings: List[Dict], max_workers: int = 5) -> List[Dict]:
        """Process filings concurrently with rate limiting and progress bar"""
        all_transactions = []
        
        # Use ThreadPoolExecutor for concurrent processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a progress bar
            with tqdm(total=len(filings), desc="Processing filings", unit="filing") as pbar:
                # Submit all tasks
                future_to_filing = {
                    executor.submit(self.parse_form4_xml, filing['url']): filing 
                    for filing in filings
                }
                
                # Process completed tasks
                for future in as_completed(future_to_filing):
                    filing = future_to_filing[future]
                    try:
                        transactions = future.result()
                        all_transactions.extend(transactions)
                    except Exception as e:
                        # Silently skip errors to avoid cluttering output
                        pass
                    finally:
                        pbar.update(1)
        
        return all_transactions
    
    def format_transaction_summary(self, summary: Dict) -> str:
        """Format transaction summary for display"""
        # Date range - fixed width for consistency
        date_str = summary['latest_date'].strftime("%m/%d")
        if summary['latest_date'].date() != summary['earliest_date'].date():
            date_str = f"{summary['earliest_date'].strftime('%m/%d')}-{summary['latest_date'].strftime('%m/%d')}"
        
        # Ticker and company name with fixed width
        ticker_company = f"{summary['ticker']} {summary['company_name']}"
        if len(ticker_company) > 28:
            ticker_company = ticker_company[:25] + "..."
        
        # Transaction summary
        trans_str = ""
        if summary['buy_count'] > 0:
            trans_str += f"{summary['buy_count']}B "
        if summary['sell_count'] > 0:
            trans_str += f"{summary['sell_count']}S"
        trans_str = trans_str.strip() or "-"
        
        # Planned indicator
        plan_str = "P" if summary['is_planned'] else " "
        
        # Net activity - consistent formatting
        net_amount = summary['net_amount']
        if net_amount == 0:
            net_str = "$0"
        else:
            net_str = self.format_amount(abs(net_amount))
            if net_amount > 0:
                net_str = "+" + net_str
            else:
                net_str = "-" + net_str
        
        # Trend indicator only
        if summary['trend'] in ["BUYING", "NET BUY"]:
            trend = "↑"
        elif summary['trend'] in ["SELLING", "NET SELL"]:
            trend = "↓"
        else:
            trend = "→"
        
        # Format roles (abbreviated)
        roles = summary['roles']
        if len(roles) > 18:
            roles = roles[:15] + "..."
        
        return f"{date_str:11} {ticker_company:28} {trans_str:7} {plan_str} {trend} {net_str:>10}  {roles:18}"

def parse_args():
    """Parse command line arguments"""
    # Custom argument parsing to handle the specific format
    amount_shown = 30
    hide_planned = False
    min_amount = None
    min_buy = None
    min_sell = None
    date_range = None
    sort_by_most = False
    force_refresh = False
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        # Check if this argument looks like a date range (contains '/' or is 'today')
        if ('/' in arg or arg.lower() == 'today') and date_range is None:
            date_range = arg
        elif arg == '-hp':
            hide_planned = True
        elif arg == '-m':
            sort_by_most = True
        elif arg == '--refresh':
            force_refresh = True
        elif arg == '-min' and i + 1 < len(sys.argv):
            i += 1
            value_str = sys.argv[i]
            
            # Parse the minimum value
            if value_str.startswith('+'):
                # Buy minimum
                try:
                    min_buy = float(value_str[1:])
                except ValueError:
                    print(f"Invalid minimum buy amount: {value_str}")
                    sys.exit(1)
            elif value_str.startswith('-'):
                # Sell minimum
                try:
                    min_sell = float(value_str[1:])
                except ValueError:
                    print(f"Invalid minimum sell amount: {value_str}")
                    sys.exit(1)
            else:
                # Absolute minimum
                try:
                    min_amount = float(value_str)
                except ValueError:
                    print(f"Invalid minimum amount: {value_str}")
                    sys.exit(1)
        elif arg.isdigit():
            # Amount to show
            amount_shown = int(arg)
        else:
            print(f"Unknown argument: {arg}")
            print(__doc__)
            sys.exit(1)
        
        i += 1
    
    return amount_shown, hide_planned, min_amount, min_buy, min_sell, date_range, sort_by_most, force_refresh

def main():
    # Parse arguments
    amount_shown, hide_planned, min_amount, min_buy, min_sell, date_range_str, sort_by_most, force_refresh = parse_args()
    
    parser = Form4Parser()
    
    # Check if user is trying to use filters without a cache
    has_filters = any([hide_planned, min_amount is not None, min_buy is not None, min_sell is not None, sort_by_most])
    has_cache = parser.is_cache_valid()
    
    if has_filters and not has_cache and not force_refresh:
        print("❌ Error: No cached data available for filtering.")
        print("Please run without filters first to build the cache:")
        print("  python latest_form4.py 50")
        print("\nThen you can use filters:")
        print("  python latest_form4.py 10 -min 100000")
        print("  python latest_form4.py 20 -hp")
        print("  python latest_form4.py 15 -m")
        sys.exit(1)
    
    # Parse date range if specified
    date_range = None
    if date_range_str:
        try:
            date_range = parser.parse_date_range(date_range_str)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    print("\nSEC Form 4 Insider Trading - 2025")
    
    # Display active filters
    filters_active = []
    if hide_planned:
        filters_active.append("No planned transactions")
    if min_amount is not None:
        filters_active.append(f"Min amount: {parser.format_amount(min_amount)}")
    if min_buy is not None:
        filters_active.append(f"Min buy: {parser.format_amount(min_buy)}")
    if min_sell is not None:
        filters_active.append(f"Min sell: {parser.format_amount(min_sell)}")
    if date_range:
        start_date, end_date = date_range
        if date_range_str.lower() == 'today':
            filters_active.append("Today only")
        else:
            filters_active.append(f"Date range: {start_date.strftime('%m/%d/%y')} - {end_date.strftime('%m/%d/%y')}")
    if sort_by_most:
        filters_active.append("Sorted by most active")
    
    if filters_active:
        print(f"Filters: {', '.join(filters_active)}")
    
    print("-" * 78)
    
    # Adjust header based on sort mode
    if sort_by_most:
        print("Date        Ticker/Company               B/S     P   Net        Trans  Roles")
    else:
        print("Date        Ticker/Company               B/S     P   Net        Roles")
    print("-" * 78)
    
    # Check if we can use cached transaction data for filtering
    all_transactions = []
    
    if not date_range and not force_refresh and parser.is_cache_valid():
        # Check if cache date matches today
        if parser.is_cache_date_current():
            print("Using cached transaction data (up to date)...")
            all_transactions = parser.load_cache()
            if all_transactions is None:
                all_transactions = []
            use_cached_data = True
        else:
            # Cache exists but is not current - need to pull new data and merge
            print("Cache is outdated, fetching new filings and merging with cache...")
            cached_transactions = parser.load_cache()
            if cached_transactions is None:
                cached_transactions = []
            
            # Get recent filings - only pull today's data
            filings = parser.get_recent_filings(days_back=1, date_range=date_range, use_cache=False)
            
            if filings:
                print(f"Found {len(filings)} new filings. Processing...")
                new_transactions = parser.process_filings_concurrently(filings, max_workers=5)
                
                # Merge new transactions with cached ones
                all_transactions = cached_transactions + new_transactions
                
                # Save merged data to cache
                if all_transactions:
                    parser.save_cache(new_transactions, merge_with_existing=True)
            else:
                print("No new filings found, using cached data...")
                all_transactions = cached_transactions
                # Update cache date even if no new filings
                parser.save_cache([], merge_with_existing=True)
    else:
        # Get recent filings - increased days back for more data
        print("Fetching recent filings...")
        filings = parser.get_recent_filings(days_back=10, date_range=date_range, use_cache=False)
        
        if not filings:
            print("No filings found.")
            return
        
        print(f"Found {len(filings)} filings. Processing...")
        
        # Process filings concurrently with progress bar
        all_transactions = parser.process_filings_concurrently(filings, max_workers=5)
        
        # Save transaction data to cache
        if all_transactions:
            parser.save_cache(all_transactions, merge_with_existing=False)
    
    # Group and analyze transactions with filters
    summaries = parser.group_transactions(
        all_transactions, 
        hide_planned=hide_planned,
        min_amount=min_amount,
        min_buy=min_buy,
        min_sell=min_sell,
        date_range=date_range
    )
    
    # Sort by most active if requested
    if sort_by_most:
        summaries.sort(key=lambda x: x['total_count'], reverse=True)
    
    # Display results
    for summary in summaries[:amount_shown]:
        if sort_by_most:
            # Modified format to show transaction count
            line = parser.format_transaction_summary(summary)
            # Insert transaction count before roles
            parts = line.rsplit('  ', 1)
            line_with_count = f"{parts[0]}  {summary['total_count']:3d}  {parts[1]}"
            print(line_with_count)
        else:
            print(parser.format_transaction_summary(summary))
    
    # Overall statistics
    print("-" * 78)
    total_buy_companies = sum(1 for s in summaries if s['trend'] in ["BUYING", "NET BUY"])
    total_sell_companies = sum(1 for s in summaries if s['trend'] in ["SELLING", "NET SELL"])
    
    notes = []
    if not hide_planned:
        notes.append("P = Planned (10b5-1)")
    
    print(f"\n{total_buy_companies} companies buying | {total_sell_companies} companies selling")
    if notes:
        print(' | '.join(notes))
    
    # Transaction count for date range if specified
    if date_range:
        total_trans_in_range = sum(s['total_count'] for s in summaries)
        print(f"Total in date range: {total_trans_in_range} transactions")
    
    print(f"Total: {len(summaries)} companies, {len(all_transactions)} transactions\n")
    
    if len(summaries) > amount_shown:
        print(f"(Showing {amount_shown} of {len(summaries)} companies)")

if __name__ == "__main__":
    main()