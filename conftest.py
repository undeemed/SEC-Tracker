"""
Pytest configuration and shared fixtures for SEC-Tracker tests.
"""

import pytest
import os
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


# =============================================================================
# Environment Fixtures
# =============================================================================

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv('SEC_USER_AGENT', 'Test User test@example.com')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'sk-or-v1-test-key-12345')
    monkeypatch.setenv('OPENROUTER_MODEL', 'deepseek/deepseek-chat-v3.1:free')


@pytest.fixture
def clean_env(monkeypatch):
    """Remove environment variables for testing missing config scenarios."""
    monkeypatch.delenv('SEC_USER_AGENT', raising=False)
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    monkeypatch.delenv('OPENROUTER_MODEL', raising=False)


# =============================================================================
# Temporary File/Directory Fixtures
# =============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_env_file(temp_dir):
    """Create a temporary .env file."""
    env_file = temp_dir / '.env'
    env_file.write_text('')
    return env_file


@pytest.fixture
def temp_cache_dir(temp_dir):
    """Create a temporary cache directory."""
    cache_dir = temp_dir / 'cache'
    cache_dir.mkdir()
    return cache_dir


# =============================================================================
# Mock Data Fixtures
# =============================================================================

@pytest.fixture
def sample_company_tickers():
    """Sample company tickers data from SEC."""
    return {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
        "2": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
        "3": {"cik_str": 1318605, "ticker": "TSLA", "title": "Tesla, Inc."},
        "4": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."},
    }


@pytest.fixture
def sample_form4_transaction():
    """Sample Form 4 transaction data."""
    return {
        'date': '2025-01-15',
        'datetime': datetime(2025, 1, 15),
        'ticker': 'AAPL',
        'company_name': 'Apple Inc.',
        'owner_name': 'John Doe',
        'price': 150.50,
        'type': 'buy',
        'planned': False,
        'shares': 1000,
        'amount': 150500.0,
        'role': 'Chief Executive Officer',
        'accession': '0001234567-25-000001'
    }


@pytest.fixture
def sample_form4_xml():
    """Sample Form 4 XML content."""
    return '''<?xml version="1.0"?>
<ownershipDocument>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerName>Apple Inc.</issuerName>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001234567</rptOwnerCik>
            <rptOwnerName>John Doe</rptOwnerName>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isOfficer>1</isOfficer>
            <officerTitle>Chief Executive Officer</officerTitle>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <transactionDate>
                <value>2025-01-15</value>
            </transactionDate>
            <transactionCoding>
                <transactionFormType>4</transactionFormType>
                <transactionCode>P</transactionCode>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares>
                    <value>1000</value>
                </transactionShares>
                <transactionPricePerShare>
                    <value>150.50</value>
                </transactionPricePerShare>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>'''


@pytest.fixture
def sample_filing_state():
    """Sample filing state data."""
    return {
        "last_check": datetime.now().isoformat(),
        "filings": {
            "0001234567-25-000001": {
                "form": "10-K",
                "filing_date": "2025-01-10",
                "downloaded_at": datetime.now().isoformat(),
                "doc_url": "https://www.sec.gov/Archives/edgar/data/320193/000123456725000001/aapl-20250110.htm"
            },
            "0001234567-25-000002": {
                "form": "8-K",
                "filing_date": "2025-01-15",
                "downloaded_at": datetime.now().isoformat(),
                "doc_url": "https://www.sec.gov/Archives/edgar/data/320193/000123456725000002/aapl-8k.htm"
            }
        },
        "analyzed": {
            "10-K": (datetime.now() - timedelta(days=1)).isoformat(),
            "8-K": (datetime.now() - timedelta(hours=12)).isoformat()
        },
        "companies": {
            "AAPL": {"cik": "0000320193", "ticker": "AAPL", "name": "Apple Inc."}
        }
    }


@pytest.fixture
def sample_sec_submissions():
    """Sample SEC submissions API response."""
    return {
        "cik": "320193",
        "entityType": "operating",
        "sic": "3571",
        "sicDescription": "Electronic Computers",
        "name": "Apple Inc.",
        "tickers": ["AAPL"],
        "filings": {
            "recent": {
                "accessionNumber": [
                    "0001234567-25-000001",
                    "0001234567-25-000002",
                    "0001234567-25-000003"
                ],
                "filingDate": [
                    "2025-01-10",
                    "2025-01-08",
                    "2025-01-05"
                ],
                "form": [
                    "10-K",
                    "8-K",
                    "4"
                ],
                "primaryDocument": [
                    "aapl-20250110.htm",
                    "aapl-8k.htm",
                    "xslF345X03/doc4.xml"
                ]
            }
        }
    }


# =============================================================================
# Mock Response Fixtures
# =============================================================================

@pytest.fixture
def mock_requests_get():
    """Create a mock for requests.get."""
    with patch('requests.get') as mock_get:
        yield mock_get


@pytest.fixture
def mock_successful_response():
    """Create a successful mock response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    return mock_response


# =============================================================================
# HTML Content Fixtures
# =============================================================================

@pytest.fixture
def sample_filing_html():
    """Sample SEC filing HTML content."""
    return '''<!DOCTYPE html>
<html>
<head><title>SEC Filing</title></head>
<body>
<div class="header">
    <h1>Apple Inc. - 10-K Filing</h1>
</div>
<div class="content">
    <p>This is a sample SEC filing document.</p>
    <table>
        <tr><td>Revenue</td><td>$394.3 billion</td></tr>
        <tr><td>Net Income</td><td>$96.9 billion</td></tr>
    </table>
    <p>Risk factors include market competition and supply chain issues.</p>
</div>
<script>console.log("test");</script>
<style>.test { color: red; }</style>
</body>
</html>'''
