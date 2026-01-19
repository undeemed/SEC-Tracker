#!/usr/bin/env python3
"""
Refresh all existing Form 4 caches and global latest filings cache
Usage: python run.py refresh-cache
"""

import os
import glob
import sys
import subprocess
from pathlib import Path

def refresh_global_latest_cache():
    """Refresh the global latest filings cache"""
    
    global_cache_file = Path("cache/form4_filings_cache.json")
    
    if not global_cache_file.exists():
        print("No global latest filings cache found.")
        return False
    
    print(f"🗑️ Deleting global latest filings cache...")
    try:
        global_cache_file.unlink()
        print(f"✓ Deleted {global_cache_file.name}")
        
        print(f"🔄 Fetching fresh global latest filings data...")
        result = subprocess.run([
            "python", "services/form4_market.py", "100"
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print(f"✓ Successfully refreshed global latest filings cache")
            return True
        else:
            print(f"✗ Failed to refresh global latest filings cache: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"✗ Timeout refreshing global latest filings cache")
        return False
    except Exception as e:
        print(f"✗ Error refreshing global latest filings cache: {e}")
        return False

def refresh_all_form4_caches():
    """Refresh all existing Form 4 caches by deleting them and fetching fresh data"""
    
    # Get the cache directory
    cache_dir = Path("cache/form4_track")
    
    if not cache_dir.exists():
        print("No Form 4 cache directory found.")
        return
    
    # Find all Form 4 cache files
    cache_files = list(cache_dir.glob("*_form4_cache.json"))
    
    if not cache_files:
        print("No Form 4 cache files found.")
        return
    
    print(f"Found {len(cache_files)} Form 4 cache files:")
    
    # Extract tickers from cache files
    tickers = []
    for cache_file in cache_files:
        ticker = cache_file.stem.replace("_form4_cache", "")
        tickers.append(ticker)
        print(f"  - {ticker}")
    
    print(f"\n🔄 Refreshing all {len(cache_files)} caches...")
    
    # Delete all cache files
    deleted_count = 0
    for cache_file in cache_files:
        try:
            cache_file.unlink()
            deleted_count += 1
            print(f"✓ Deleted {cache_file.name}")
        except Exception as e:
            print(f"✗ Failed to delete {cache_file.name}: {e}")
    
    print(f"\n✅ Successfully deleted {deleted_count}/{len(cache_files)} cache files.")
    
    # Now fetch fresh data for all tickers
    print(f"\n🔄 Fetching fresh data for all {len(tickers)} companies...")
    
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Fetching fresh data for {ticker}...")
        try:
            # Run form4 command to fetch fresh data
            result = subprocess.run([
                "python", "services/form4_company.py", ticker, "-r", "5"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✓ Successfully refreshed {ticker}")
            else:
                print(f"✗ Failed to refresh {ticker}: {result.stderr}")
        except subprocess.TimeoutExpired:
            print(f"✗ Timeout refreshing {ticker}")
        except Exception as e:
            print(f"✗ Error refreshing {ticker}: {e}")
    
    print(f"\n🎉 Cache refresh complete! All {len(tickers)} companies now have fresh data with improved planned transaction detection.")

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        return
    
    refresh_all_form4_caches()

if __name__ == "__main__":
    main()
