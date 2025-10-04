#!/usr/bin/env python3
"""
Simple command wrapper - no setup needed
Usage: python run.py <command> <args>
"""

import sys
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

commands = {
    "scan": "cik_lookup.py",
    "fetch": "scraper.py",
    "download": "download.py",
    "track": "sec_filing_tracker.py",
    "analyze": "filing_analyzer.py",
    "monitor": "sec_filing_monitor.py",
    "form4": "track_form4.py",
    "latest": "latest_form4.py",
    "trade": "trade_analysis.py",
    "update-key": "update_api_key.py",
    "refresh-cache": "refresh_form4_cache.py",
    "refresh-latest": "refresh_latest_cache.py"
}

if len(sys.argv) < 2:
    print("SEC Filing Tracker - Available Commands:")
    print()
    
    # Command descriptions
    cmd_descriptions = {
        "scan": "Lookup CIK numbers for ticker symbols",
        "fetch": "Download SEC filings for analysis", 
        "download": "Manual filing download utility",
        "track": "Main command - Smart tracking with analysis",
        "analyze": "AI-powered filing analysis",
        "monitor": "Monitor filings for changes",
        "form4": "Insider trading (Form 4) tracker",
        "latest": "Recent insider transactions",
        "trade": "Trade analysis (coming soon)",
        "update-key": "Update OpenRouter API key",
        "refresh-cache": "Refresh all Form 4 caches (company-specific)",
        "refresh-latest": "Refresh global latest filings cache"
    }
    
    print("Main Commands:")
    for cmd, file in commands.items():
        desc = cmd_descriptions.get(cmd, "")
        if cmd == "update-key":
            print(f"  python run.py {cmd:<15} - {desc}")
        elif cmd in ["refresh-cache", "refresh-latest"]:
            print(f"  python run.py {cmd:<15} - {desc}")
        else:
            print(f"  python run.py {cmd:<15} <ticker> - {desc}")
    
    print()
    print("Model Management:")
    print("  python run.py model              - Show current AI model")
    print("  python run.py model -switch|-s   - Switch AI model interactively")
    print("  python run.py model -switch -slot 1  - Switch model and save to slot 1")
    print("  python run.py model -list-slots  - List configured model slots")
    print("  python run.py model -load-slot 1 - Load model from slot 1")
    
    print()
    print("Multi Commands:")
    print("  python run.py multi update-all   - Update all tracked companies")
    print("  python run.py multi add-list <file> - Add multiple tickers from file")
    
    print()
    print("Examples:")
    print("  python run.py track AAPL         - Track Apple filings")
    print("  python run.py form4 TSLA -hp     - Show Tesla Form 4s (hide planned)")
    print("  python run.py latest 50           - Show 50 recent insider transactions")
    print("  python run.py refresh-cache       - Refresh all Form 4 caches")
    sys.exit(0)

cmd = sys.argv[1]
args = sys.argv[2:]

# Handle model command
if cmd == "model":
    from api_key_utils import get_current_model, switch_model
    
    if not args or (len(args) == 1 and args[0] in ["-h", "--help"]):
        # Show current model
        current_model = get_current_model()
        print(f"Current model: {current_model}")
    elif args[0] in ["-switch", "-s"]:
        # Interactive model switch
        slot = None
        # Look for -slot argument
        for i, arg in enumerate(args[1:]):
            if arg == "-slot" and i+2 < len(args):
                # Next argument is the slot number
                slot_num = args[i+2]
                if slot_num.isdigit():
                    slot = int(slot_num)
                    break
                else:
                    print("Error: Slot must be a number (e.g., -slot 1)")
                    sys.exit(1)
            elif arg.startswith("-slot"):
                # Slot number is part of the same argument
                slot_part = arg.replace("-slot", "").strip()
                if slot_part.isdigit():
                    slot = int(slot_part)
                    break
                else:
                    print("Error: Slot must be a number (e.g., -slot 1)")
                    sys.exit(1)
        switch_model(slot)
    elif args[0] == "-list-slots":
        # List configured model slots
        from api_key_utils import list_model_slots
        list_model_slots()
    elif args[0] == "-load-slot":
        # Load model from slot
        if len(args) < 2:
            print("Usage: python run.py model -load-slot <number>")
        else:
            try:
                slot_num = int(args[1])
                from api_key_utils import get_slot_model, set_model
                model = get_slot_model(slot_num)
                if model:
                    set_model(model)
                    print(f"Switched to slot {slot_num}: {model}")
                else:
                    print(f"No model configured in slot {slot_num}")
            except ValueError:
                print("Error: Slot must be a number")
    else:
        print("Usage:")
        print("  python run.py model                     - Show current model")
        print("  python run.py model -switch|-s          - Switch model")
        print("  python run.py model -switch -slot 1     - Switch model and save to slot 1")
        print("  python run.py model -list-slots         - List configured model slots")
        print("  python run.py model -load-slot 1        - Load model from slot 1")
elif cmd in commands:
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