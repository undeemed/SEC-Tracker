#!/usr/bin/env python3
"""
SEC Filing Tracker - CLI Entry Point
Usage: python run.py <command> <args>
"""

import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Command mapping to module paths
commands = {
    # Core commands
    "scan": "utils/cik.py",
    "fetch": "core/scraper.py",
    "download": "core/downloader.py",
    "track": "core/tracker.py",
    "analyze": "core/analyzer.py",
    
    # Service commands
    "form4": "services/form4_company.py",
    "latest": "services/form4_market.py",
    "monitor": "services/monitor.py",
    
    # Utility commands
    "update-key": "utils/api_keys.py",
    "refresh-cache": "scripts/refresh_cache.py",
    "refresh-latest": "scripts/refresh_latest.py"
}

# Command descriptions for help
cmd_descriptions = {
    "scan": "Lookup CIK numbers for ticker symbols",
    "fetch": "Download SEC filings for analysis", 
    "download": "Manual filing download utility",
    "track": "Main command - Smart tracking with analysis",
    "analyze": "AI-powered filing analysis",
    "monitor": "Monitor filings for changes",
    "form4": "Insider trading (Form 4) tracker",
    "latest": "Recent insider transactions",
    "update-key": "Update OpenRouter API key",
    "refresh-cache": "Refresh all Form 4 caches (company-specific)",
    "refresh-latest": "Refresh global latest filings cache"
}

def print_help():
    """Print help message with all available commands"""
    print("SEC Filing Tracker - Available Commands:")
    print()
    
    print("Core Commands:")
    for cmd in ["track", "fetch", "download", "analyze", "scan"]:
        desc = cmd_descriptions.get(cmd, "")
        if cmd == "track":
            print(f"  python run.py {cmd:<15} <ticker> - {desc} ⭐")
        else:
            print(f"  python run.py {cmd:<15} <ticker> - {desc}")
    
    print()
    print("Service Commands:")
    for cmd in ["form4", "latest", "monitor"]:
        desc = cmd_descriptions.get(cmd, "")
        if cmd == "monitor":
            print(f"  python run.py {cmd:<15}          - {desc}")
        else:
            print(f"  python run.py {cmd:<15} <args>   - {desc}")
    
    print()
    print("Utility Commands:")
    for cmd in ["update-key", "refresh-cache", "refresh-latest"]:
        desc = cmd_descriptions.get(cmd, "")
        print(f"  python run.py {cmd:<15}          - {desc}")
    
    print()
    print("Model Management:")
    print("  python run.py model              - Show current AI model")
    print("  python run.py model -switch|-s   - Switch AI model interactively")
    print("  python run.py model -switch -slot 1  - Switch model and save to slot")
    print("  python run.py model -list-slots  - List configured model slots")
    print("  python run.py model -load-slot 1 - Load model from slot")
    
    print()
    print("Multi Commands:")
    print("  python run.py multi update-all   - Update all tracked companies")
    print("  python run.py multi add-list <file> - Add multiple tickers from file")
    
    print()
    print("Examples:")
    print("  python run.py track AAPL         - Track Apple filings")
    print("  python run.py form4 TSLA -hp     - Show Tesla Form 4s (hide planned)")
    print("  python run.py latest 50          - Show 50 recent insider transactions")

def handle_model_command(args):
    """Handle model management commands"""
    from utils.api_keys import get_current_model, switch_model, list_model_slots, get_slot_model, set_model
    
    if not args or (len(args) == 1 and args[0] in ["-h", "--help"]):
        current_model = get_current_model()
        print(f"Current model: {current_model}")
    elif args[0] in ["-switch", "-s"]:
        slot = None
        for i, arg in enumerate(args[1:]):
            if arg == "-slot" and i+2 < len(args):
                slot_num = args[i+2]
                if slot_num.isdigit():
                    slot = int(slot_num)
                    break
                else:
                    print("Error: Slot must be a number (e.g., -slot 1)")
                    sys.exit(1)
            elif arg.startswith("-slot"):
                slot_part = arg.replace("-slot", "").strip()
                if slot_part.isdigit():
                    slot = int(slot_part)
                    break
                else:
                    print("Error: Slot must be a number (e.g., -slot 1)")
                    sys.exit(1)
        switch_model(slot)
    elif args[0] == "-list-slots":
        list_model_slots()
    elif args[0] == "-load-slot":
        if len(args) < 2:
            print("Usage: python run.py model -load-slot <number>")
        else:
            try:
                slot_num = int(args[1])
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
        print("  python run.py model -switch -slot 1     - Switch and save to slot")
        print("  python run.py model -list-slots         - List configured slots")
        print("  python run.py model -load-slot 1        - Load from slot")

def handle_multi_command(args):
    """Handle multi-company commands"""
    if not args:
        print("Multi commands: update-all, add-list <file>")
        return
    
    if args[0] == "update-all":
        result = subprocess.run(
            ["python", "core/tracker.py", "--list-companies"], 
            capture_output=True, text=True
        )
        for line in result.stdout.split('\n'):
            if line.strip().startswith('- '):
                ticker = line.split(':')[0].replace('- ', '').strip()
                if ticker:
                    print(f"Updating {ticker}...")
                    subprocess.run(["python", "core/tracker.py", ticker])
    
    elif args[0] == "add-list" and len(args) > 1:
        with open(args[1], 'r') as f:
            for line in f:
                ticker = line.strip()
                if ticker and not ticker.startswith('#'):
                    print(f"Adding {ticker}...")
                    subprocess.run(["python", "core/tracker.py", ticker])

def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    # Handle special commands
    if cmd == "model":
        handle_model_command(args)
    elif cmd == "multi":
        handle_multi_command(args)
    elif cmd in commands:
        subprocess.run(["python", commands[cmd]] + args)
    else:
        print(f"Unknown command: {cmd}")
        print("Available:", ", ".join(commands.keys()), "+ model, multi")
        sys.exit(1)

if __name__ == "__main__":
    main()
