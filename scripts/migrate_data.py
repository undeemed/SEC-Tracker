#!/usr/bin/env python3
"""
Data Migration Script

Migrates existing local JSON data to PostgreSQL database.
Run this after setting up the database with Alembic migrations.

Usage:
    python scripts/migrate_data.py [--dry-run] [--verbose]
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def migrate_form4_cache(*, dry_run: bool = False, verbose: bool = False) -> int:
    """Migrate Form 4 cache files to database."""
    from sqlalchemy import select
    from db.session import get_db_session, init_db
    from models.transaction import Form4Transaction
    
    await init_db()
    
    cache_dir = Path("cache/form4_track")
    if not cache_dir.exists():
        print("No Form 4 cache directory found, skipping...")
        return 0
    
    migrated = 0
    
    async for db in get_db_session():
        for cache_file in cache_dir.glob("*_form4_cache.json"):
            ticker = cache_file.stem.replace("_form4_cache", "")
            
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                
                transactions = data.get("transactions", [])
                
                for trans in transactions:
                    # Check if already exists
                    existing = await db.execute(
                        select(Form4Transaction).where(
                            Form4Transaction.ticker == ticker,
                            Form4Transaction.accession_number == trans.get("accession")
                        )
                    )
                    
                    if existing.scalar_one_or_none():
                        if verbose:
                            print(f"  Skipping existing transaction {ticker}/{trans.get('accession')}")
                        continue
                    
                    # Parse date
                    trans_date = None
                    if trans.get("date"):
                        try:
                            trans_date = datetime.strptime(trans["date"], "%Y-%m-%d").date()
                        except (ValueError, TypeError):
                            pass
                    
                    # Create record
                    record = Form4Transaction(
                        id=uuid4(),
                        ticker=ticker,
                        company_name=trans.get("company_name"),
                        owner_name=trans.get("owner_name", "Unknown"),
                        role=trans.get("role"),
                        transaction_type=trans.get("type", "unknown"),
                        is_planned=trans.get("planned", False),
                        shares=trans.get("shares"),
                        price=trans.get("price"),
                        amount=trans.get("amount"),
                        transaction_date=trans_date,
                        accession_number=trans.get("accession")
                    )
                    
                    if not dry_run:
                        db.add(record)
                    migrated += 1
                
                if not dry_run:
                    await db.commit()
                print(f"  Migrated {ticker}: {len(transactions)} transactions")
                
            except Exception as e:
                print(f"  Error migrating {cache_file}: {e}")
                await db.rollback()
    
    return migrated


async def migrate_filings_cache(*, dry_run: bool = False, verbose: bool = False) -> int:
    """Migrate filing state data to database."""
    from sqlalchemy import select
    from db.session import get_db_session, init_db
    from models.filing import Filing
    
    await init_db()
    
    state_file = Path("filing_state.json")
    if not state_file.exists():
        print("No filing state file found, skipping...")
        return 0
    
    migrated = 0
    
    try:
        with open(state_file) as f:
            data = json.load(f)
        
        filings = data.get("filings", {})
        companies = data.get("companies", {})
        
        async for db in get_db_session():
            for accession, filing_data in filings.items():
                existing = await db.execute(
                    select(Filing).where(Filing.accession_number == accession)
                )
                if existing.scalar_one_or_none():
                    if verbose:
                        print(f"  Skipping existing filing {accession}")
                    continue

                # Try to find company info
                cik = "UNKNOWN"
                ticker = "UNKNOWN"
                
                for t, company in companies.items():
                    ticker = t
                    cik = company.get("cik", "UNKNOWN")
                    break
                
                # Parse date
                filing_date = None
                if filing_data.get("filing_date"):
                    try:
                        filing_date = datetime.strptime(filing_data["filing_date"], "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        filing_date = datetime.now().date()
                
                record = Filing(
                    id=uuid4(),
                    ticker=ticker,
                    cik=cik,
                    accession_number=accession,
                    form_type=filing_data.get("form", "UNKNOWN"),
                    filing_date=filing_date or datetime.now().date(),
                    document_url=filing_data.get("doc_url")
                )
                
                if not dry_run:
                    db.add(record)
                migrated += 1
            
            if not dry_run:
                await db.commit()
            print(f"  Migrated {migrated} filings")
            
    except Exception as e:
        print(f"  Error migrating filings: {e}")
    
    return migrated


async def migrate_latest_cache(*, dry_run: bool = False, verbose: bool = False) -> int:
    """Migrate global Form 4 latest cache."""
    from sqlalchemy import select
    from db.session import get_db_session, init_db
    from models.transaction import Form4Transaction
    
    await init_db()
    
    cache_file = Path("cache/form4_filings_cache.json")
    if not cache_file.exists():
        print("No latest cache file found, skipping...")
        return 0
    
    migrated = 0
    
    try:
        with open(cache_file) as f:
            data = json.load(f)
        
        filings = data.get("filings", [])
        
        async for db in get_db_session():
            for filing in filings:
                ticker = filing.get("ticker", "UNKNOWN")
                accession = filing.get("accession")
                
                for trans in filing.get("transactions", []):
                    if accession:
                        existing = await db.execute(
                            select(Form4Transaction).where(
                                Form4Transaction.ticker == ticker,
                                Form4Transaction.accession_number == accession,
                            )
                        )
                        if existing.scalar_one_or_none():
                            if verbose:
                                print(f"  Skipping existing latest transaction {ticker}/{accession}")
                            continue

                    trans_date = None
                    if trans.get("date"):
                        try:
                            trans_date = datetime.strptime(trans["date"], "%Y-%m-%d").date()
                        except (ValueError, TypeError):
                            pass
                    
                    record = Form4Transaction(
                        id=uuid4(),
                        ticker=ticker,
                        company_name=filing.get("company_name"),
                        owner_name=trans.get("owner_name", "Unknown"),
                        role=trans.get("role"),
                        transaction_type=trans.get("type", "unknown"),
                        is_planned=trans.get("planned", False),
                        shares=trans.get("shares"),
                        price=trans.get("price"),
                        amount=trans.get("amount"),
                        transaction_date=trans_date,
                        accession_number=accession
                    )
                    
                    if not dry_run:
                        db.add(record)
                    migrated += 1
            
            if not dry_run:
                await db.commit()
            print(f"  Migrated {migrated} transactions from latest cache")
            
    except Exception as e:
        print(f"  Error migrating latest cache: {e}")
    
    return migrated


async def main():
    """Run all migrations."""
    print("=" * 60)
    print("SEC-Tracker Data Migration")
    print("=" * 60)
    print()
    
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv
    
    if dry_run:
        print("DRY RUN - No data will be written\n")
    
    print("1. Migrating Form 4 company cache...")
    form4_count = await migrate_form4_cache(dry_run=dry_run, verbose=verbose)
    
    print("\n2. Migrating filing state...")
    filings_count = await migrate_filings_cache(dry_run=dry_run, verbose=verbose)
    
    print("\n3. Migrating latest Form 4 cache...")
    latest_count = await migrate_latest_cache(dry_run=dry_run, verbose=verbose)
    
    print()
    print("=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"  Form 4 transactions: {form4_count}")
    print(f"  Filings: {filings_count}")
    print(f"  Latest transactions: {latest_count}")
    print(f"  Total records: {form4_count + filings_count + latest_count}")
    print()
    print("Migration complete!")


if __name__ == "__main__":
    asyncio.run(main())
