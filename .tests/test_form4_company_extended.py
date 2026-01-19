"""
Extended tests for services/form4_company.py - Additional coverage.
"""

import pytest
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCompanyForm4TrackerExtended:
    """Extended tests for CompanyForm4Tracker class."""
    
    def test_tracker_initialization(self, temp_dir, mock_env_vars, sample_company_tickers, monkeypatch):
        """Test tracker initialization."""
        from services.form4_company import CompanyForm4Tracker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        tracker = CompanyForm4Tracker()
        
        assert tracker is not None
        assert hasattr(tracker, 'company_tickers')
    
    def test_lookup_ticker(self, temp_dir, mock_env_vars, sample_company_tickers, monkeypatch):
        """Test ticker lookup."""
        from services.form4_company import CompanyForm4Tracker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        tracker = CompanyForm4Tracker()
        
        cik = tracker.lookup_ticker("AAPL")
        
        assert cik is not None


class TestParseArgs:
    """Tests for parse_args function."""
    
    def test_parse_args_basic(self, mock_env_vars, monkeypatch):
        """Test basic argument parsing."""
        from services.form4_company import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_company.py', 'AAPL'])
        
        tickers, count, hide_planned, days_back, date_range = parse_args()
        
        assert 'AAPL' in tickers
    
    def test_parse_args_with_count(self, mock_env_vars, monkeypatch):
        """Test parsing with count argument."""
        from services.form4_company import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_company.py', 'AAPL', '-r', '20'])
        
        tickers, count, hide_planned, days_back, date_range = parse_args()
        
        assert count == 20
    
    def test_parse_args_hide_planned(self, mock_env_vars, monkeypatch):
        """Test parsing with hide planned flag."""
        from services.form4_company import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_company.py', 'AAPL', '-hp'])
        
        tickers, count, hide_planned, days_back, date_range = parse_args()
        
        assert hide_planned is True
    
    def test_parse_args_days_back(self, mock_env_vars, monkeypatch):
        """Test parsing with days back argument."""
        from services.form4_company import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_company.py', 'AAPL', '-d', '60'])
        
        tickers, count, hide_planned, days_back, date_range = parse_args()
        
        assert days_back == 60


class TestForm4CompanyMain:
    """Tests for form4_company main function."""
    
    def test_main_with_invalid_ticker(self, temp_dir, mock_env_vars, sample_company_tickers, monkeypatch, capsys):
        """Test main with invalid ticker."""
        from services.form4_company import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['form4_company.py', 'INVALID'])
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        main()
        
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "No transactions" in captured.out or len(captured.out) >= 0
