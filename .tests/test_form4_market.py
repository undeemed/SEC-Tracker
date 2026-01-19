"""
Tests for services/form4_market.py - Market-wide Form 4 tracking.
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestForm4Parser:
    """Tests for Form4Parser class."""
    
    def test_parser_creation(self, mock_env_vars, temp_dir, monkeypatch):
        """Test Form4Parser can be created."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        assert parser is not None
    
    def test_parse_date_range_today(self, mock_env_vars, temp_dir, monkeypatch):
        """Test parsing 'today' date range."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        start, end = parser.parse_date_range('today')
        
        today = datetime.now().date()
        assert start.date() == today
    
    def test_parse_date_range_explicit(self, mock_env_vars, temp_dir, monkeypatch):
        """Test parsing explicit date range."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        start, end = parser.parse_date_range('1/15/25 - 1/20/25')
        
        assert start.month == 1
        assert start.day == 15
        assert end.month == 1
        assert end.day == 20
    
    def test_is_cache_valid_no_file(self, mock_env_vars, temp_dir, monkeypatch):
        """Test cache validity when no file exists."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        assert parser.is_cache_valid() is False
    
    def test_is_cache_valid_with_file(self, mock_env_vars, temp_dir, monkeypatch):
        """Test cache validity when file exists."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache directory and file
        cache_dir = temp_dir / 'cache'
        cache_dir.mkdir()
        cache_file = cache_dir / 'form4_filings_cache.json'
        cache_file.write_text(json.dumps({
            'cache_date': datetime.now().isoformat(),
            'transactions': []
        }))
        
        parser = Form4Parser()
        assert parser.is_cache_valid() is True
    
    def test_get_cache_date(self, mock_env_vars, temp_dir, monkeypatch):
        """Test getting cache date."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        cache_dir = temp_dir / 'cache'
        cache_dir.mkdir()
        cache_file = cache_dir / 'form4_filings_cache.json'
        
        now = datetime.now()
        cache_file.write_text(json.dumps({
            'cache_date': now.isoformat(),
            'transactions': []
        }))
        
        parser = Form4Parser()
        cache_date = parser.get_cache_date()
        
        assert cache_date is not None
        assert cache_date.date() == now.date()
    
    def test_save_and_load_cache(self, mock_env_vars, temp_dir, sample_form4_transaction, monkeypatch):
        """Test saving and loading cache."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        # Save
        parser.save_cache([sample_form4_transaction], merge_with_existing=False)
        
        # Load
        loaded = parser.load_cache()
        
        assert loaded is not None
        assert len(loaded) == 1
    
    def test_abbreviate_role(self, mock_env_vars, temp_dir, monkeypatch):
        """Test role abbreviation."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        assert parser.abbreviate_role('Chief Executive Officer') == 'CEO'
        assert parser.abbreviate_role('Director') == 'Dir'
    
    def test_format_amount(self, mock_env_vars, temp_dir, monkeypatch):
        """Test amount formatting."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        result = parser.format_amount(1_000_000)
        assert '$1' in result and 'M' in result


class TestGroupTransactions:
    """Tests for group_transactions method."""
    
    def test_group_by_ticker(self, mock_env_vars, temp_dir, sample_form4_transaction, monkeypatch):
        """Test grouping transactions by ticker."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        transactions = [sample_form4_transaction]
        grouped = parser.group_transactions(transactions)
        
        assert len(grouped) == 1
        assert grouped[0]['ticker'] == 'AAPL'
    
    def test_group_calculates_totals(self, mock_env_vars, temp_dir, sample_form4_transaction, monkeypatch):
        """Test that grouping calculates buy/sell totals."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        buy_trans = sample_form4_transaction.copy()
        buy_trans['type'] = 'buy'
        buy_trans['amount'] = 100000
        
        sell_trans = sample_form4_transaction.copy()
        sell_trans['type'] = 'sell'
        sell_trans['amount'] = 50000
        
        transactions = [buy_trans, sell_trans]
        grouped = parser.group_transactions(transactions)
        
        assert len(grouped) == 1
        assert grouped[0]['buy_amount'] == 100000
        assert grouped[0]['sell_amount'] == 50000
        assert grouped[0]['net_amount'] == 50000
    
    def test_group_with_hide_planned(self, mock_env_vars, temp_dir, sample_form4_transaction, monkeypatch):
        """Test filtering planned transactions."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        planned_trans = sample_form4_transaction.copy()
        planned_trans['planned'] = True
        
        unplanned_trans = sample_form4_transaction.copy()
        unplanned_trans['planned'] = False
        unplanned_trans['ticker'] = 'NVDA'
        
        transactions = [planned_trans, unplanned_trans]
        grouped = parser.group_transactions(transactions, hide_planned=True)
        
        # Should only include NVDA (unplanned)
        tickers = [g['ticker'] for g in grouped]
        assert 'NVDA' in tickers
    
    def test_group_with_min_amount_filter(self, mock_env_vars, temp_dir, sample_form4_transaction, monkeypatch):
        """Test filtering by minimum amount."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        small_trans = sample_form4_transaction.copy()
        small_trans['amount'] = 1000
        small_trans['ticker'] = 'SMALL'
        
        large_trans = sample_form4_transaction.copy()
        large_trans['amount'] = 1_000_000
        large_trans['ticker'] = 'LARGE'
        
        transactions = [small_trans, large_trans]
        grouped = parser.group_transactions(transactions, min_amount=500_000)
        
        # Should only include LARGE
        tickers = [g['ticker'] for g in grouped]
        assert 'LARGE' in tickers
        assert 'SMALL' not in tickers
    
    def test_group_determines_trend(self, mock_env_vars, temp_dir, sample_form4_transaction, monkeypatch):
        """Test trend determination."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        buy_trans = sample_form4_transaction.copy()
        buy_trans['type'] = 'buy'
        
        transactions = [buy_trans]
        grouped = parser.group_transactions(transactions)
        
        assert grouped[0]['trend'] == 'BUYING'


class TestFormatTransactionSummary:
    """Tests for format_transaction_summary method."""
    
    def test_format_summary_structure(self, mock_env_vars, temp_dir, monkeypatch):
        """Test summary formatting structure."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        summary = {
            'ticker': 'AAPL',
            'company_name': 'Apple Inc.',
            'latest_date': datetime.now(),
            'earliest_date': datetime.now() - timedelta(days=5),
            'buy_count': 2,
            'sell_count': 1,
            'net_amount': 100000,
            'trend': 'NET BUY',
            'is_planned': False,
            'roles': 'CEO'
        }
        
        formatted = parser.format_transaction_summary(summary)
        
        assert 'AAPL' in formatted
        assert 'Apple' in formatted


class TestParseArgs:
    """Tests for parse_args function."""
    
    def test_parse_default_args(self, mock_env_vars, monkeypatch):
        """Test parsing with default arguments."""
        from services.form4_market import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_market.py'])
        
        amount, hide_planned, min_amount, min_buy, min_sell, date_range, sort_by_most, force_refresh = parse_args()
        
        assert amount == 30  # Default
        assert hide_planned is False
    
    def test_parse_with_amount(self, mock_env_vars, monkeypatch):
        """Test parsing with amount argument."""
        from services.form4_market import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_market.py', '50'])
        
        amount, hide_planned, min_amount, min_buy, min_sell, date_range, sort_by_most, force_refresh = parse_args()
        
        assert amount == 50
    
    def test_parse_with_hide_planned(self, mock_env_vars, monkeypatch):
        """Test parsing with -hp flag."""
        from services.form4_market import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_market.py', '-hp'])
        
        amount, hide_planned, min_amount, min_buy, min_sell, date_range, sort_by_most, force_refresh = parse_args()
        
        assert hide_planned is True
    
    def test_parse_with_min_amount(self, mock_env_vars, monkeypatch):
        """Test parsing with -min flag."""
        from services.form4_market import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_market.py', '-min', '100000'])
        
        amount, hide_planned, min_amount, min_buy, min_sell, date_range, sort_by_most, force_refresh = parse_args()
        
        assert min_amount == 100000
    
    def test_parse_with_min_buy(self, mock_env_vars, monkeypatch):
        """Test parsing with -min +X flag."""
        from services.form4_market import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_market.py', '-min', '+500000'])
        
        amount, hide_planned, min_amount, min_buy, min_sell, date_range, sort_by_most, force_refresh = parse_args()
        
        assert min_buy == 500000
    
    def test_parse_with_min_sell(self, mock_env_vars, monkeypatch):
        """Test parsing with -min -X flag."""
        from services.form4_market import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_market.py', '-min', '-1000000'])
        
        amount, hide_planned, min_amount, min_buy, min_sell, date_range, sort_by_most, force_refresh = parse_args()
        
        assert min_sell == 1000000
    
    def test_parse_with_sort_flag(self, mock_env_vars, monkeypatch):
        """Test parsing with -m sort flag."""
        from services.form4_market import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_market.py', '-m'])
        
        amount, hide_planned, min_amount, min_buy, min_sell, date_range, sort_by_most, force_refresh = parse_args()
        
        assert sort_by_most is True


class TestForm4MarketEdgeCases:
    """Tests for edge cases in market-wide Form 4 tracking."""
    
    def test_handles_empty_transactions(self, mock_env_vars, temp_dir, monkeypatch):
        """Test handling empty transactions list."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        grouped = parser.group_transactions([])
        
        assert grouped == []
    
    def test_handles_invalid_date_range(self, mock_env_vars, temp_dir, monkeypatch):
        """Test handling invalid date range."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        with pytest.raises(ValueError):
            parser.parse_date_range('invalid-date')
    
    def test_cache_merge_prevents_duplicates(self, mock_env_vars, temp_dir, sample_form4_transaction, monkeypatch):
        """Test that cache merging prevents duplicates."""
        from services.form4_market import Form4Parser
        
        monkeypatch.chdir(temp_dir)
        
        parser = Form4Parser()
        
        # Save first batch
        parser.save_cache([sample_form4_transaction], merge_with_existing=False)
        
        # Save same transaction again
        parser.save_cache([sample_form4_transaction], merge_with_existing=True)
        
        # Should not have duplicates
        loaded = parser.load_cache()
        assert len(loaded) == 1
