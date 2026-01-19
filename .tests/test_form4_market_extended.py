"""
Extended tests for services/form4_market.py - Additional coverage.
"""

import pytest
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestForm4ParserExtended:
    """Extended tests for Form4Parser class."""
    
    def test_get_recent_filings_daily_index(self, temp_dir, mock_env_vars, monkeypatch):
        """Test getting filings from daily index."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        # Mock daily index response
        index_content = """
Form Type|Company Name|CIK|Date Filed|File Name
------------------------------------------------------------------------
4|APPLE INC|0000320193|2025-01-15|edgar/data/320193/0001-25-001.txt
4|NVIDIA CORP|0001045810|2025-01-15|edgar/data/1045810/0001-25-002.txt
        """
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = index_content
        
        with patch('requests.get', return_value=mock_response):
            filings = parser.get_recent_filings(days_back=1, use_cache=False)
        
        assert isinstance(filings, list)
    
    def test_get_recent_filings_atom_fallback(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test falling back to ATOM feed."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        # First request fails (daily index)
        fail_response = MagicMock()
        fail_response.status_code = 404
        
        # ATOM feed response
        atom_xml = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>4 - APPLE INC</title>
                <link rel="alternate" href="https://example.com/filing"/>
                <updated>2025-01-15T12:00:00Z</updated>
            </entry>
        </feed>
        """
        
        atom_response = MagicMock()
        atom_response.status_code = 200
        atom_response.content = atom_xml.encode()
        
        with patch('requests.get', side_effect=[fail_response, atom_response]):
            filings = parser.get_recent_filings(days_back=1, use_cache=False)
        
        # May find filings from ATOM feed
        assert isinstance(filings, list)
    
    def test_parse_form4_xml_full(self, temp_dir, mock_env_vars, sample_form4_xml, monkeypatch):
        """Test full XML parsing from market parser."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        # Mock index page
        index_response = MagicMock()
        index_response.status_code = 200
        index_response.text = '<a href="form4.xml">Form 4</a>'
        
        # Mock XML response
        xml_response = MagicMock()
        xml_response.status_code = 200
        xml_response.text = sample_form4_xml
        
        with patch('requests.get', side_effect=[index_response, xml_response]):
            transactions = parser.parse_form4_xml("https://example.com/filing-index.htm")
        
        assert isinstance(transactions, list)
    
    def test_process_filings_concurrently(self, temp_dir, mock_env_vars, monkeypatch):
        """Test concurrent filing processing."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        filings = [
            {"url": "https://example.com/filing1", "date": datetime.now(), "title": "Test 1"},
            {"url": "https://example.com/filing2", "date": datetime.now(), "title": "Test 2"}
        ]
        
        with patch.object(parser, 'parse_form4_xml', return_value=[]):
            transactions = parser.process_filings_concurrently(filings, max_workers=2)
        
        assert isinstance(transactions, list)
    
    def test_is_cache_sufficient_for_count(self, temp_dir, mock_env_vars, sample_form4_transaction, monkeypatch):
        """Test cache sufficiency checking."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        
        trans = sample_form4_transaction.copy()
        trans['datetime'] = datetime.now().isoformat()
        trans['accession'] = "0001-25-001"
        
        cache_data = {
            "cache_date": datetime.now().isoformat(),
            "transactions": [trans],
            "cached_filings_count": 1
        }
        
        cache_file = cache_dir / "form4_filings_cache.json"
        cache_file.write_text(json.dumps(cache_data))
        
        parser = Form4Parser()
        
        # Should be sufficient for 1
        assert parser.is_cache_sufficient_for_count(1) is True
        
        # Should not be sufficient for 100
        assert parser.is_cache_sufficient_for_count(100) is False
    
    def test_is_cache_date_current(self, temp_dir, mock_env_vars, monkeypatch):
        """Test cache date currency checking."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        
        # Current date cache
        cache_data = {
            "cache_date": datetime.now().isoformat(),
            "transactions": []
        }
        
        cache_file = cache_dir / "form4_filings_cache.json"
        cache_file.write_text(json.dumps(cache_data))
        
        parser = Form4Parser()
        
        assert parser.is_cache_date_current() is True
    
    def test_get_most_recent_transaction_date(self, temp_dir, mock_env_vars, sample_form4_transaction, monkeypatch):
        """Test getting most recent transaction date."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        
        trans = sample_form4_transaction.copy()
        trans['datetime'] = datetime(2025, 1, 15).isoformat()
        
        cache_data = {
            "cache_date": datetime.now().isoformat(),
            "transactions": [trans]
        }
        
        (cache_dir / "form4_filings_cache.json").write_text(json.dumps(cache_data))
        
        parser = Form4Parser()
        
        result = parser.get_most_recent_transaction_date()
        
        assert result is not None


class TestGroupTransactionsExtended:
    """Extended tests for group_transactions."""
    
    def test_group_with_date_range(self, temp_dir, mock_env_vars, sample_form4_transaction, monkeypatch):
        """Test grouping with date range filter."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        trans = sample_form4_transaction.copy()
        trans['datetime'] = datetime(2025, 1, 15)
        
        date_range = (datetime(2025, 1, 1), datetime(2025, 1, 31))
        
        grouped = parser.group_transactions([trans], date_range=date_range)
        
        assert len(grouped) > 0
    
    def test_group_with_min_buy_filter(self, temp_dir, mock_env_vars, sample_form4_transaction, monkeypatch):
        """Test grouping with minimum buy filter."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        trans = sample_form4_transaction.copy()
        trans['datetime'] = datetime.now()
        trans['type'] = 'buy'
        trans['amount'] = 1_000_000
        
        grouped = parser.group_transactions([trans], min_buy=500_000)
        
        assert len(grouped) > 0
    
    def test_group_with_min_sell_filter(self, temp_dir, mock_env_vars, sample_form4_transaction, monkeypatch):
        """Test grouping with minimum sell filter."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        trans = sample_form4_transaction.copy()
        trans['datetime'] = datetime.now()
        trans['type'] = 'sell'
        trans['amount'] = 1_000_000
        
        grouped = parser.group_transactions([trans], min_sell=500_000)
        
        assert len(grouped) > 0


class TestForm4MarketMain:
    """Tests for form4_market main function."""
    
    def test_main_with_filters_no_cache(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test main with filters but no cache."""
        from services.form4_market import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['form4_market.py', '-hp'])
        
        with pytest.raises(SystemExit):
            main()
        
        captured = capsys.readouterr()
        assert "No cached data available" in captured.out
    
    def test_main_with_refresh(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test main with --refresh flag."""
        from services.form4_market import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['form4_market.py', '--refresh', '10'])
        
        # Mock the filings fetch
        mock_response = MagicMock()
        mock_response.status_code = 404  # No index available
        
        with patch('requests.get', return_value=mock_response):
            main()
        
        captured = capsys.readouterr()
        # Should complete even with no filings
        assert "SEC Form 4" in captured.out
    
    def test_main_with_date_range(self, temp_dir, mock_env_vars, sample_form4_transaction, monkeypatch, capsys):
        """Test main with date range."""
        from services.form4_market import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['form4_market.py', 'today'])
        
        # Create cache
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        
        trans = sample_form4_transaction.copy()
        trans['datetime'] = datetime.now().isoformat()
        
        cache_data = {
            "cache_date": datetime.now().isoformat(),
            "transactions": [trans],
            "cached_filings_count": 100
        }
        
        (cache_dir / "form4_filings_cache.json").write_text(json.dumps(cache_data))
        
        main()
        
        captured = capsys.readouterr()
        assert "SEC Form 4" in captured.out


class TestFormatTransactionSummaryExtended:
    """Extended tests for format_transaction_summary."""
    
    def test_format_with_multiple_roles(self, temp_dir, mock_env_vars, monkeypatch):
        """Test formatting with multiple roles."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        summary = {
            'ticker': 'AAPL',
            'company_name': 'Apple Inc.',
            'latest_date': datetime.now(),
            'earliest_date': datetime.now() - timedelta(days=5),
            'buy_count': 3,
            'sell_count': 2,
            'net_amount': -50000,  # Net sell
            'trend': 'NET SELL',
            'is_planned': True,
            'roles': 'CEO, CFO, Director'
        }
        
        formatted = parser.format_transaction_summary(summary)
        
        assert 'AAPL' in formatted
        assert '↓' in formatted  # Sell indicator
