"""
Tests for core/scraper.py - SEC EDGAR scraping functionality.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestIsWithinLookbackPeriod:
    """Tests for is_within_lookback_period function."""
    
    def test_filing_within_period(self, mock_env_vars):
        """Test filing within lookback period."""
        from core.scraper import is_within_lookback_period
        
        # Recent filing should be within 90 days
        recent_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        assert is_within_lookback_period(recent_date, "4") is True
    
    def test_filing_outside_period(self, mock_env_vars):
        """Test filing outside lookback period."""
        from core.scraper import is_within_lookback_period
        
        # Old filing should be outside 90 days
        old_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        assert is_within_lookback_period(old_date, "4") is False
    
    def test_different_form_types_have_different_lookbacks(self, mock_env_vars):
        """Test that different form types have different lookback periods."""
        from core.scraper import is_within_lookback_period, FORM_LOOKBACK_DAYS
        
        # 10-K has 365 day lookback
        date_300_days_ago = (datetime.now() - timedelta(days=300)).strftime("%Y-%m-%d")
        assert is_within_lookback_period(date_300_days_ago, "10-K") is True
        
        # Form 4 has 90 day lookback
        assert is_within_lookback_period(date_300_days_ago, "4") is False


class TestFetchRecentForms:
    """Tests for fetch_recent_forms function."""
    
    def test_fetch_forms_returns_dict(self, mock_env_vars, sample_sec_submissions):
        """Test that fetch_recent_forms returns a dictionary."""
        from core.scraper import fetch_recent_forms
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = sample_sec_submissions
        
        with patch('requests.get', return_value=mock_response):
            result = fetch_recent_forms("0000320193", ["10-K", "8-K"], 5)
            
            assert isinstance(result, dict)
            assert "10-K" in result
            assert "8-K" in result
    
    def test_fetch_forms_structure(self, mock_env_vars, sample_sec_submissions):
        """Test that fetched forms have correct structure."""
        from core.scraper import fetch_recent_forms
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = sample_sec_submissions
        
        with patch('requests.get', return_value=mock_response):
            result = fetch_recent_forms("0000320193", ["10-K"], 5)
            
            if result["10-K"]:
                filing = result["10-K"][0]
                assert "accession" in filing
                assert "doc_url" in filing
                assert "form" in filing
                assert "filing_date" in filing
    
    def test_fetch_forms_respects_max_limit(self, mock_env_vars):
        """Test that max_per_form limit is respected."""
        from core.scraper import fetch_recent_forms
        
        # Create response with many filings
        many_filings = {
            "filings": {
                "recent": {
                    "accessionNumber": [f"000-{i}" for i in range(20)],
                    "filingDate": [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(20)],
                    "form": ["10-K"] * 20,
                    "primaryDocument": [f"doc{i}.htm" for i in range(20)]
                }
            }
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = many_filings
        
        with patch('requests.get', return_value=mock_response):
            result = fetch_recent_forms("0000320193", ["10-K"], max_per_form=3)
            
            assert len(result["10-K"]) <= 3
    
    def test_fetch_forms_with_from_date_filter(self, mock_env_vars, sample_sec_submissions):
        """Test filtering by from_date."""
        from core.scraper import fetch_recent_forms
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = sample_sec_submissions
        
        # Filter to only include filings after a certain date
        from_date = "2025-01-09"
        
        with patch('requests.get', return_value=mock_response):
            result = fetch_recent_forms("0000320193", ["10-K", "8-K"], 5, from_date=from_date)
            
            # All returned filings should be after from_date
            for form_type, filings in result.items():
                for filing in filings:
                    assert filing["filing_date"] > from_date


class TestFetchByTicker:
    """Tests for fetch_by_ticker function."""
    
    def test_fetch_by_ticker_valid(self, mock_env_vars, temp_dir, sample_company_tickers, monkeypatch):
        """Test fetching filings by valid ticker."""
        import json
        from core.scraper import fetch_by_ticker
        
        monkeypatch.chdir(temp_dir)
        
        # Create ticker cache
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        # Mock SEC API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "filings": {
                "recent": {
                    "accessionNumber": ["000-1"],
                    "filingDate": ["2025-01-10"],
                    "form": ["10-K"],
                    "primaryDocument": ["doc.htm"]
                }
            }
        }
        
        with patch('requests.get', return_value=mock_response):
            result = fetch_by_ticker("AAPL")
            
            assert "company" in result
            assert "filings" in result
            assert result["company"]["ticker"] == "AAPL"
    
    def test_fetch_by_ticker_invalid_raises(self, mock_env_vars, temp_dir, sample_company_tickers, monkeypatch):
        """Test fetching filings by invalid ticker raises ValueError."""
        import json
        from core.scraper import fetch_by_ticker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        with pytest.raises(ValueError, match="not found"):
            fetch_by_ticker("INVALID_TICKER_XYZ")


class TestScraperConfiguration:
    """Tests for scraper configuration."""
    
    def test_default_forms_configured(self, mock_env_vars):
        """Test that default forms are configured."""
        from core.scraper import FORMS_TO_GRAB
        
        assert "10-K" in FORMS_TO_GRAB
        assert "10-Q" in FORMS_TO_GRAB
        assert "8-K" in FORMS_TO_GRAB
        assert "4" in FORMS_TO_GRAB
    
    def test_form_lookback_days_configured(self, mock_env_vars):
        """Test that form lookback days are configured."""
        from core.scraper import FORM_LOOKBACK_DAYS
        
        assert "10-K" in FORM_LOOKBACK_DAYS
        assert "10-Q" in FORM_LOOKBACK_DAYS
        assert "8-K" in FORM_LOOKBACK_DAYS
        assert "4" in FORM_LOOKBACK_DAYS
        
        # 10-K should have longer lookback than Form 4
        assert FORM_LOOKBACK_DAYS["10-K"] > FORM_LOOKBACK_DAYS["4"]


class TestScraperURLConstruction:
    """Tests for URL construction in scraper."""
    
    def test_doc_url_format(self, mock_env_vars, sample_sec_submissions):
        """Test that document URLs are correctly formatted."""
        from core.scraper import fetch_recent_forms
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = sample_sec_submissions
        
        with patch('requests.get', return_value=mock_response):
            result = fetch_recent_forms("0000320193", ["10-K"], 5)
            
            if result["10-K"]:
                url = result["10-K"][0]["doc_url"]
                assert url.startswith("https://www.sec.gov/Archives/edgar/data/")
                assert ".htm" in url or ".xml" in url


class TestScraperErrorHandling:
    """Tests for error handling in scraper."""
    
    def test_handles_api_error_gracefully(self, mock_env_vars):
        """Test that API errors are handled gracefully."""
        from core.scraper import fetch_recent_forms
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server Error")
        
        with patch('requests.get', return_value=mock_response):
            with pytest.raises(Exception):
                fetch_recent_forms("0000320193", ["10-K"], 5)
    
    def test_handles_malformed_response(self, mock_env_vars):
        """Test handling of malformed API response."""
        from core.scraper import fetch_recent_forms
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"unexpected": "format"}
        
        with patch('requests.get', return_value=mock_response):
            # Should handle gracefully
            with pytest.raises(KeyError):
                fetch_recent_forms("0000320193", ["10-K"], 5)
