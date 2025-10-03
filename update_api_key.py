#!/usr/bin/env python3
"""
Update OpenRouter API Key
This script helps you update your OpenRouter API key if it's invalid or expired.
"""

from dotenv import load_dotenv
from api_key_utils import save_api_key_to_env
import os

load_dotenv()

print("\n" + "="*70)
print("          OpenRouter API Key Update")
print("="*70)

current_key = os.getenv('OPENROUTER_API_KEY')
if current_key:
    print(f"\nCurrent API key: {current_key[:15]}...{current_key[-8:] if len(current_key) > 23 else ''}")
else:
    print("\nNo API key currently configured.")

print("\n" + "="*70)
print("How to get a new OpenRouter API key:")
print("="*70)
print("\n  1. Visit: https://openrouter.ai/keys")
print("  2. Sign in with Google/GitHub/Discord")
print("  3. Click 'Create Key' button")
print("  4. Give it a name (e.g., 'SEC Filing Analyzer')")
print("  5. Copy the key (starts with 'sk-or-v1-')")
print("\n  Note: Free tier includes $1 in credits for testing!")
print("        Most free models use ~$0.001 per analysis")
print("="*70 + "\n")

new_key = input("Enter your new OpenRouter API key (or press Enter to cancel): ").strip()

if new_key:
    if new_key.startswith('sk-or-v1-'):
        save_api_key_to_env('OPENROUTER_API_KEY', new_key)
        print("\n✅ API key updated successfully!")
        print("You can now run analysis commands.")
    else:
        print("\n⚠️  Warning: API key should start with 'sk-or-v1-'")
        confirm = input("Save anyway? (y/N): ").strip().lower()
        if confirm == 'y':
            save_api_key_to_env('OPENROUTER_API_KEY', new_key)
            print("\n✅ API key saved.")
        else:
            print("\n❌ API key not saved.")
else:
    print("\n❌ No changes made.")

print("\nTo test your API key, run:")
print("  python filing_analyzer.py AAPL --forms 10-K")
print()

