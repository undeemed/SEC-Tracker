#!/usr/bin/env python3
"""
Simple command wrapper - no setup needed
Usage: python run.py <command> <args>
"""

import sys
import subprocess

commands = {
    "scan": "cik_lookup.py",
    "fetch": "scraper.py",
    "download": "download.py",
    "track": "sec_filing_tracker.py",
    "analyze": "deepseek_optimized.py",
    "monitor": "sec_filing_monitor.py",
    "form4": "track_form4.py",
    "latest": "latest_form4.py",
    "trade": "trade_analysis.py"
}

if len(sys.argv) < 2:
    print("Commands:")
    for cmd in commands:
        print(f"  python run.py {cmd} <ticker>")
    sys.exit(0)

cmd = sys.argv[1]
args = sys.argv[2:]

if cmd in commands:
    subprocess.run(["python", commands[cmd]] + args)
elif cmd == "multi":
    if not args:
        print("Multi commands: update-all, add-list <file>")
    elif args[0] == "update-all":
        # Get all tracked companies and update them
        result = subprocess.run(["python", "sec_filing_tracker.py", "--list-companies"], 
                              capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if line.strip().startswith('- '):
                ticker = line.split(':')[0].replace('- ', '').strip()
                if ticker:
                    print(f"Updating {ticker}...")
                    subprocess.run(["python", "sec_filing_tracker.py", ticker])
    elif args[0] == "add-list" and len(args) > 1:
        with open(args[1], 'r') as f:
            for line in f:
                ticker = line.strip()
                if ticker and not ticker.startswith('#'):
                    print(f"Adding {ticker}...")
                    subprocess.run(["python", "sec_filing_tracker.py", ticker])
else:
    print(f"Unknown command: {cmd}")
    print("Available:", ", ".join(commands.keys()), "+ multi")