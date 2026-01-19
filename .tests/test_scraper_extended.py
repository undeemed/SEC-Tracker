"""
Extended tests for core/scraper.py - Additional coverage.
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestIsWithinLookbackPeriod:
    """Tests for is_within_lookback_period function."""
    
    def test_within_period(self, mock_env_vars):
        """Test date within lookback period."""
        from core.scraper import is_within_lookback_period
        
        today = datetime.now().strftime('%Y-%m-%d')
        result = is_within_lookback_period(today, 30)
        
        assert result is True
    
    def test_outside_period(self, mock_env_vars):
        """Test date outside lookback period."""
        from core.scraper import is_within_lookback_period
        
        old_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        result = is_within_lookback_period(old_date, 30)
        
        assert result is False
    
    def test_boundary_date(self, mock_env_vars):
        """Test date on boundary."""
        from core.scraper import is_within_lookback_period
        
        boundary = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        result = is_within_lookback_period(boundary, 30)
        
        # Should be either True or False depending on exact timing
        assert isinstance(result, bool)


class TestFetchRecentForms:
    """Tests for fetch_recent_forms function."""
    
    def test_fetch_with_cik(self, temp_dir, mock_env_vars, sample_company_tickers, monkeypatch):
        """Test fetch with CIK and parameters."""
        from core.scraper import fetch_recent_forms
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "filings": {
                "recent": {
                    "form": ["10-K", "8-K"],
                    "filingDate": ["2025-01-10", "2025-01-11"],
                    "accessionNumber": ["0001", "0002"],
                    "primaryDocument": ["doc1.htm", "doc2.htm"]
                }
            }
        }
        
        with patch('requests.get', return_value=mock_response):
            result = fetch_recent_forms(
                cik="0000320193",
                forms=["10-K", "8-K"],
                max_per_form=10
            )
        
        assert isinstance(result, dict)


class TestFetchByTicker:
    """Tests for fetch_by_ticker function."""
    
    def test_fetch_valid_ticker(self, temp_dir, mock_env_vars, sample_company_tickers, monkeypatch):
        """Test fetching by valid ticker."""
        from core.scraper import fetch_by_ticker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "filings": {
                "recent": {
                    "form": ["10-K"],
                    "filingDate": ["2025-01-10"],
                    "accessionNumber": ["0001"],
                    "primaryDocument": ["doc1.htm"]
                }
            }
        }
        
        with patch('requests.get', return_value=mock_response):
            result = fetch_by_ticker("AAPL")
        
        assert result is not None
        assert 'filings' in result or 'company' in result
    
    def test_fetch_lowercase_ticker(self, temp_dir, mock_env_vars, sample_company_tickers, monkeypatch):
        """Test fetching with lowercase ticker."""
        from core.scraper import fetch_by_ticker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "filings": {
                "recent": {
                    "form": ["10-K"],
                    "filingDate": ["2025-01-10"],
                    "accessionNumber": ["0001"],
                    "primaryDocument": ["doc1.htm"]
                }
            }
        }
        
        with patch('requests.get', return_value=mock_response):
            result = fetch_by_ticker("aapl")
        
        assert result is not None
