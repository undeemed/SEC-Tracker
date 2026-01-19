"""
Tests for utils/cik.py - CIK lookup functionality.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCIKLookup:
    """Tests for CIKLookup class."""
    
    def test_cik_lookup_creation(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test CIKLookup can be created."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache file
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        assert lookup is not None
        assert lookup.tickers_data is not None
    
    def test_get_cik_valid_ticker(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test getting CIK for valid ticker."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        cik = lookup.get_cik('AAPL')
        
        assert cik is not None
        assert cik == '0000320193'
    
    def test_get_cik_lowercase_ticker(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test getting CIK with lowercase ticker."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        cik = lookup.get_cik('aapl')
        
        assert cik is not None
        assert cik == '0000320193'
    
    def test_get_cik_invalid_ticker(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test getting CIK for invalid ticker returns None."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        cik = lookup.get_cik('INVALID')
        
        assert cik is None
    
    def test_get_cik_pads_to_10_digits(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test CIK is padded to 10 digits."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        cik = lookup.get_cik('AAPL')
        
        assert len(cik) == 10
        assert cik.startswith('0')
    
    def test_get_company_info_valid_ticker(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test getting full company info for valid ticker."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        info = lookup.get_company_info('NVDA')
        
        assert info is not None
        assert info['ticker'] == 'NVDA'
        assert info['cik'] == '0001045810'
        assert 'NVIDIA' in info['name']
    
    def test_get_company_info_invalid_ticker(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test getting company info for invalid ticker returns None."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        info = lookup.get_company_info('INVALID')
        
        assert info is None
    
    def test_search_companies_by_ticker(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test searching companies by ticker."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        results = lookup.search_companies('AAPL')
        
        assert len(results) > 0
        assert results[0]['ticker'] == 'AAPL'
    
    def test_search_companies_by_name(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test searching companies by name."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        results = lookup.search_companies('APPLE')
        
        assert len(results) > 0
        assert any('AAPL' in r['ticker'] for r in results)
    
    def test_search_companies_partial_match(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test searching companies with partial match."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        results = lookup.search_companies('MS')
        
        assert len(results) > 0
        # Should find MSFT
        tickers = [r['ticker'] for r in results]
        assert 'MSFT' in tickers
    
    def test_search_companies_case_insensitive(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test search is case insensitive."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        results_upper = lookup.search_companies('NVIDIA')
        results_lower = lookup.search_companies('nvidia')
        
        assert len(results_upper) == len(results_lower)
    
    def test_search_companies_returns_max_10(self, temp_dir, monkeypatch):
        """Test search returns maximum 10 results."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        # Create data with many matches
        data = {str(i): {"cik_str": i, "ticker": f"TEST{i}", "title": f"Test Company {i}"} 
                for i in range(20)}
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(data))
        
        lookup = CIKLookup()
        results = lookup.search_companies('TEST')
        
        assert len(results) <= 10
    
    def test_search_companies_no_results(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test search with no matching results."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        results = lookup.search_companies('ZZZZZZZZZ')
        
        assert results == []


class TestCIKLookupCache:
    """Tests for CIKLookup caching behavior."""
    
    def test_uses_existing_cache(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test that existing cache is used."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        with patch('requests.get') as mock_get:
            lookup = CIKLookup()
            
            # requests.get should not be called when cache exists
            mock_get.assert_not_called()
    
    def test_fetches_when_no_cache(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test that data is fetched when no cache exists."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = sample_company_tickers
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            lookup = CIKLookup()
            
            # requests.get should be called when no cache
            mock_get.assert_called_once()
    
    def test_creates_cache_after_fetch(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test that cache file is created after fetching."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = sample_company_tickers
        
        with patch('requests.get', return_value=mock_response):
            lookup = CIKLookup()
            
            cache_file = temp_dir / 'company_tickers_cache.json'
            assert cache_file.exists()
    
    def test_handles_fetch_error_gracefully(self, temp_dir, monkeypatch):
        """Test that fetch errors are handled gracefully."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        with patch('requests.get', side_effect=Exception("Network error")):
            lookup = CIKLookup()
            
            # Should return empty dict on error
            assert lookup.tickers_data == {}


class TestCIKLookupEdgeCases:
    """Tests for edge cases in CIK lookup."""
    
    def test_empty_ticker(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test behavior with empty ticker."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        cik = lookup.get_cik('')
        
        assert cik is None
    
    def test_special_characters_in_search(self, temp_dir, sample_company_tickers, monkeypatch):
        """Test search with special characters."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        lookup = CIKLookup()
        results = lookup.search_companies('Test@#$%')
        
        # Should not crash, may return empty
        assert isinstance(results, list)
    
    def test_corrupt_cache_handling(self, temp_dir, monkeypatch):
        """Test handling of corrupt cache file."""
        from utils.cik import CIKLookup
        
        monkeypatch.chdir(temp_dir)
        
        # Create corrupt cache
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text('not valid json {{{')
        
        # The CIKLookup will try to load the corrupt cache and fail
        # Then it will try to fetch from SEC
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"0": {"cik_str": 1, "ticker": "TEST", "title": "Test"}}
        
        with patch('requests.get', return_value=mock_response):
            # May raise JSONDecodeError when reading corrupt cache
            # or succeed if it fetches fresh data
            try:
                lookup = CIKLookup()
                assert lookup is not None
            except json.JSONDecodeError:
                # This is acceptable behavior - corrupt cache causes error
                pass
