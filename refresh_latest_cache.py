#!/usr/bin/env python3
"""
Refresh the global latest filings cache
Usage: python run.py refresh-latest
"""

import os
import sys
import subprocess
from pathlib import Path

def refresh_latest_cache():
    """Refresh the global latest filings cache by deleting it and fetching fresh data"""
    
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
            "python", "latest_form4.py", "100"
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

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        return
    
    print("🔄 Refreshing global latest filings cache...")
    success = refresh_latest_cache()
    
    if success:
        print(f"\n🎉 Global latest filings cache refresh complete!")
        print("Next 'latest' commands will use fresh data with improved planned transaction detection.")
    else:
        print(f"\n❌ Global latest filings cache refresh failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
