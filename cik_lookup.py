#!/usr/bin/env python3
"""
CIK Lookup Module
Maps ticker symbols to CIK numbers using SEC's company tickers file
"""

import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List

class CIKLookup:
    """Handles ticker to CIK conversion"""
    
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    CACHE_FILE = "company_tickers_cache.json"
    CACHE_DURATION = timedelta(days=7)  # Refresh weekly
    
    def __init__(self):
        self.cache_file = Path(self.CACHE_FILE)
        self.tickers_data = self._load_tickers()
    
    def _load_tickers(self) -> Dict:
        """Load ticker data from cache or fetch from SEC"""
        # Check if cache exists and is recent
        if self.cache_file.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(self.cache_file.stat().st_mtime)
            if cache_age < self.CACHE_DURATION:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        
        # Fetch fresh data
        print("Fetching company tickers from SEC...")
        try:
            response = requests.get(self.TICKERS_URL, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            response.raise_for_status()
            data = response.json()
            
            # Save to cache
            with open(self.cache_file, 'w') as f:
                json.dump(data, f)
            
            return data
        except Exception as e:
            print(f"Error fetching tickers: {e}")
            # Try to use stale cache if available
            if self.cache_file.exists():
                print("Using stale cache...")
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            return {}
    
    def get_cik(self, ticker: str) -> Optional[str]:
        """Get CIK for a ticker symbol"""
        ticker = ticker.upper()
        
        # Search through the data
        for entry in self.tickers_data.values():
            if entry.get("ticker") == ticker:
                # Format CIK with leading zeros (10 digits)
                cik = str(entry["cik_str"]).zfill(10)
                return cik
        
        return None
    
    def get_company_info(self, ticker: str) -> Optional[Dict]:
        """Get full company information"""
        ticker = ticker.upper()
        
        for entry in self.tickers_data.values():
            if entry.get("ticker") == ticker:
                return {
                    "cik": str(entry["cik_str"]).zfill(10),
                    "ticker": entry["ticker"],
                    "name": entry["title"]
                }
        
        return None
    
    def search_companies(self, query: str) -> List[Dict]:
        """Search for companies by ticker or name"""
        query = query.upper()
        results = []
        
        for entry in self.tickers_data.values():
            ticker = entry.get("ticker", "")
            name = entry.get("title", "").upper()
            
            if query in ticker or query in name:
                results.append({
                    "cik": str(entry["cik_str"]).zfill(10),
                    "ticker": ticker,
                    "name": entry["title"]
                })
        
        # Sort by relevance (exact ticker match first)
        results.sort(key=lambda x: (x["ticker"] != query, x["ticker"]))
        return results[:10]  # Return top 10 matches


def main():
    """Test the CIK lookup functionality"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python cik_lookup.py <ticker>")
        print("       python cik_lookup.py search <query>")
        sys.exit(1)
    
    lookup = CIKLookup()
    
    if sys.argv[1].lower() == "search" and len(sys.argv) > 2:
        query = sys.argv[2]
        results = lookup.search_companies(query)
        
        if results:
            print(f"\nSearch results for '{query}':")
            print("-" * 60)
            for result in results:
                print(f"{result['ticker']:6} | {result['cik']} | {result['name']}")
        else:
            print(f"No companies found matching '{query}'")
    
    else:
        ticker = sys.argv[1]
        info = lookup.get_company_info(ticker)
        
        if info:
            print(f"\nCompany Information:")
            print("-" * 40)
            print(f"Ticker: {info['ticker']}")
            print(f"Name:   {info['name']}")
            print(f"CIK:    {info['cik']}")
        else:
            print(f"Ticker '{ticker}' not found")
            
            # Suggest similar tickers
            results = lookup.search_companies(ticker)
            if results:
                print("\nDid you mean:")
                for result in results[:5]:
                    print(f"  {result['ticker']} - {result['name']}")


if __name__ == "__main__":
    main()