"""
Tests for core/downloader.py - Filing download functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDownloadCompanyFilings:
    """Tests for download_company_filings function."""
    
    def test_creates_download_directory(self, mock_env_vars, temp_dir, monkeypatch):
        """Test that download directory is created."""
        from core.downloader import download_company_filings
        import json
        
        monkeypatch.chdir(temp_dir)
        
        # Create mock ticker cache
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps({
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }))
        
        # Mock the fetch function to return empty
        with patch('core.downloader.fetch_recent_forms', return_value={}):
            with patch('core.downloader.fetch_by_ticker', side_effect=ValueError("Not found")):
                download_company_filings("0000320193")
        
        download_dir = temp_dir / "sec_filings"
        assert download_dir.exists()
    
    def test_downloads_filing_files(self, mock_env_vars, temp_dir, monkeypatch):
        """Test that filing files are downloaded."""
        from core.downloader import download_company_filings
        import json
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps({
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }))
        
        mock_filings = {
            "10-K": [{
                "accession": "0001234-25-000001",
                "doc_url": "https://example.com/doc.htm",
                "form": "10-K",
                "filing_date": "2025-01-15"
            }]
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"<html>Test content</html>"
        
        with patch('core.downloader.fetch_recent_forms', return_value=mock_filings):
            with patch('requests.get', return_value=mock_response):
                download_company_filings("0000320193")
        
        # Check file was created
        download_dir = temp_dir / "sec_filings" / "CIK0000320193" / "10-K"
        files = list(download_dir.glob("*.html"))
        assert len(files) == 1
    
    def test_skips_existing_files(self, mock_env_vars, temp_dir, monkeypatch, capsys):
        """Test that existing files are skipped."""
        from core.downloader import download_company_filings
        import json
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps({
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }))
        
        # Pre-create the file
        download_dir = temp_dir / "sec_filings" / "CIK0000320193" / "10-K"
        download_dir.mkdir(parents=True)
        existing_file = download_dir / "0001234-25-000001.html"
        existing_file.write_text("<html>Existing</html>")
        
        mock_filings = {
            "10-K": [{
                "accession": "0001234-25-000001",
                "doc_url": "https://example.com/doc.htm",
                "form": "10-K",
                "filing_date": "2025-01-15"
            }]
        }
        
        with patch('core.downloader.fetch_recent_forms', return_value=mock_filings):
            download_company_filings("0000320193")
        
        captured = capsys.readouterr()
        assert "Exists" in captured.out


class TestDownloadByTicker:
    """Tests for download_company_filings with ticker."""
    
    def test_download_by_ticker(self, mock_env_vars, temp_dir, monkeypatch):
        """Test downloading by ticker symbol."""
        from core.downloader import download_company_filings
        import json
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps({
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }))
        
        mock_result = {
            "company": {"cik": "0000320193", "ticker": "AAPL", "name": "Apple Inc."},
            "filings": {"10-K": []}
        }
        
        with patch('core.downloader.fetch_by_ticker', return_value=mock_result):
            download_company_filings("AAPL")
        
        download_dir = temp_dir / "sec_filings" / "AAPL"
        assert download_dir.exists()


class TestDownloadErrorHandling:
    """Tests for error handling in downloader."""
    
    def test_handles_invalid_ticker(self, mock_env_vars, temp_dir, monkeypatch, capsys):
        """Test handling of invalid ticker."""
        from core.downloader import download_company_filings
        import json
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps({
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }))
        
        with patch('core.downloader.fetch_by_ticker', side_effect=ValueError("Ticker not found")):
            download_company_filings("INVALID")
        
        captured = capsys.readouterr()
        assert "Error" in captured.out or "not found" in captured.out.lower()
    
    def test_handles_download_failure(self, mock_env_vars, temp_dir, monkeypatch, capsys):
        """Test handling of download failure."""
        from core.downloader import download_company_filings
        import json
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps({
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }))
        
        mock_filings = {
            "10-K": [{
                "accession": "0001234-25-000001",
                "doc_url": "https://example.com/doc.htm",
                "form": "10-K",
                "filing_date": "2025-01-15"
            }]
        }
        
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("Download failed")
        
        with patch('core.downloader.fetch_recent_forms', return_value=mock_filings):
            with patch('requests.get', return_value=mock_response):
                download_company_filings("0000320193")
        
        captured = capsys.readouterr()
        assert "Failed" in captured.out


class TestDownloadConfiguration:
    """Tests for downloader configuration."""
    
    def test_download_dir_constant(self, mock_env_vars):
        """Test DOWNLOAD_DIR constant is defined."""
        from core.downloader import DOWNLOAD_DIR
        
        assert DOWNLOAD_DIR == "sec_filings"
    
    def test_uses_correct_user_agent(self, mock_env_vars, temp_dir, monkeypatch):
        """Test that correct user agent is used."""
        from core.downloader import download_company_filings
        import json
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps({
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }))
        
        mock_filings = {
            "10-K": [{
                "accession": "0001234-25-000001",
                "doc_url": "https://example.com/doc.htm",
                "form": "10-K",
                "filing_date": "2025-01-15"
            }]
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"<html></html>"
        
        with patch('core.downloader.fetch_recent_forms', return_value=mock_filings):
            with patch('requests.get', return_value=mock_response) as mock_get:
                download_company_filings("0000320193")
                
                # Check User-Agent header was included
                call_kwargs = mock_get.call_args[1]
                assert 'headers' in call_kwargs
                assert 'User-Agent' in call_kwargs['headers']
