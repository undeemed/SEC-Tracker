#!/usr/bin/env python3
"""
Common utilities shared across SEC Filing Tracker modules.
Centralizes configuration, rate limiting, and formatting functions.
"""

import os
import time
import threading
from typing import Dict, Optional
from datetime import datetime


# =============================================================================
# SECURITY: Centralized Configuration
# =============================================================================

def get_user_agent() -> str:
    """
    Get SEC API user agent from environment.
    SEC requires a valid contact email for API access.
    
    Returns:
        str: User agent string for SEC API requests
        
    Raises:
        EnvironmentError: If SEC_USER_AGENT is not configured
    """
    user_agent = os.getenv('SEC_USER_AGENT')
    
    if not user_agent:
        # Try to get from config module (which may prompt user)
        try:
            from config import get_user_agent as config_get_user_agent
            return config_get_user_agent()
        except ImportError:
            pass
        
        # Raise error instead of using insecure default
        raise EnvironmentError(
            "SEC_USER_AGENT environment variable is required. "
            "Set it in your .env file: SEC_USER_AGENT='Your Name your@email.com'"
        )
    
    return user_agent


def get_sec_headers() -> Dict[str, str]:
    """
    Get standard headers for SEC API requests.
    
    Returns:
        dict: Headers dictionary with User-Agent
    """
    return {
        'User-Agent': get_user_agent(),
        'Accept-Encoding': 'gzip, deflate',
        'Accept': 'application/json, text/html'
    }


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimiter:
    """
    Thread-safe rate limiter for SEC API compliance.
    SEC enforces 10 requests per second limit.
    """
    
    def __init__(self, max_requests_per_second: int = 10):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0.0
        self.lock = threading.Lock()
    
    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limit."""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()
    
    def __enter__(self):
        self.wait_if_needed()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# Global rate limiter instance for SEC API
sec_rate_limiter = RateLimiter(max_requests_per_second=10)


# =============================================================================
# Formatting Utilities
# =============================================================================

def format_amount(amount: float) -> str:
    """
    Format dollar amounts with K/M/B abbreviations.
    
    Args:
        amount: Dollar amount to format
        
    Returns:
        Formatted string (e.g., "$1.5M", "$500K")
    """
    if amount >= 1_000_000_000:
        return f"${amount/1_000_000_000:.1f}B"
    elif amount >= 1_000_000:
        return f"${amount/1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.0f}K"
    else:
        return f"${amount:.0f}"


def abbreviate_role(role: str) -> str:
    """
    Abbreviate common executive/insider role titles.
    
    Args:
        role: Full role title
        
    Returns:
        Abbreviated role string
    """
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
    
    # Truncate if still too long
    if len(role) > 30:
        role = role[:27] + '...'
    
    return role


def format_date_range(start_date: datetime, end_date: datetime) -> str:
    """
    Format a date range for display.
    
    Args:
        start_date: Start of range
        end_date: End of range
        
    Returns:
        Formatted date range string
    """
    if start_date.date() == end_date.date():
        return start_date.strftime("%m/%d/%y")
    else:
        return f"{start_date.strftime('%m/%d/%y')}-{end_date.strftime('%m/%d/%y')}"


# =============================================================================
# XML Parsing Utilities for Form 4
# =============================================================================

def parse_transaction_from_xml(trans_elem, ticker: str, relationship: str, 
                                company_name: str, accession_number: str = None) -> Optional[Dict]:
    """
    Parse a Form 4 transaction XML element into a dictionary.
    
    Args:
        trans_elem: XML Element containing transaction data
        ticker: Stock ticker symbol
        relationship: Insider's relationship to company
        company_name: Company name
        accession_number: SEC accession number for deduplication
        
    Returns:
        Dictionary with transaction details or None if parsing fails
    """
    try:
        # Transaction date
        trans_date_elem = trans_elem.find('.//transactionDate/value')
        trans_date = trans_date_elem.text if trans_date_elem is not None else ""
        
        # Parse date to datetime
        trans_datetime = datetime.strptime(trans_date, "%Y-%m-%d") if trans_date else datetime.now()
        
        # Transaction type (A=Acquired, D=Disposed, P=Purchase)
        trans_code_elem = trans_elem.find('.//transactionCoding/transactionCode')
        trans_code = trans_code_elem.text if trans_code_elem is not None else ""
        trans_type = "buy" if trans_code in ["A", "P"] else "sell"
        
        # Check if planned (10b5-1)
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
        
        transaction_data = {
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
        
        if accession_number:
            transaction_data['accession'] = accession_number
        
        return transaction_data
        
    except Exception:
        return None


# =============================================================================
# Cache Utilities
# =============================================================================

def ensure_cache_dir(subdir: str = None) -> str:
    """
    Ensure cache directory exists and return its path.
    
    Args:
        subdir: Optional subdirectory within cache/
        
    Returns:
        Path to the cache directory
    """
    from pathlib import Path
    
    cache_dir = Path("cache")
    if subdir:
        cache_dir = cache_dir / subdir
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    return str(cache_dir)


# =============================================================================
# Validation Utilities
# =============================================================================

def validate_ticker(ticker: str) -> str:
    """
    Validate and normalize a stock ticker symbol.
    
    Args:
        ticker: Raw ticker input
        
    Returns:
        Normalized ticker (uppercase, stripped)
        
    Raises:
        ValueError: If ticker is invalid
    """
    if not ticker:
        raise ValueError("Ticker symbol cannot be empty")
    
    ticker = ticker.strip().upper()
    
    # Basic validation
    if not ticker.isalpha() or len(ticker) > 5:
        # Allow some special cases like BRK.A, BRK.B
        if '.' not in ticker and '-' not in ticker:
            if not ticker.replace('.', '').replace('-', '').isalnum():
                raise ValueError(f"Invalid ticker symbol: {ticker}")
    
    return ticker
