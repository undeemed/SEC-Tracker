"""
Tests for services/form4_company.py - Company-specific Form 4 tracking.
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCompanyForm4Tracker:
    """Tests for CompanyForm4Tracker class."""
    
    def test_tracker_creation(self, mock_env_vars, temp_dir, sample_company_tickers, monkeypatch):
        """Test CompanyForm4Tracker can be created."""
        from services.form4_company import CompanyForm4Tracker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        tracker = CompanyForm4Tracker()
        assert tracker is not None
    
    def test_lookup_ticker_valid(self, mock_env_vars, temp_dir, sample_company_tickers, monkeypatch):
        """Test looking up valid ticker."""
        from services.form4_company import CompanyForm4Tracker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        tracker = CompanyForm4Tracker()
        cik, name = tracker.lookup_ticker('AAPL')
        
        assert cik is not None
        assert 'Apple' in name
    
    def test_lookup_ticker_invalid(self, mock_env_vars, temp_dir, sample_company_tickers, monkeypatch):
        """Test looking up invalid ticker."""
        from services.form4_company import CompanyForm4Tracker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        tracker = CompanyForm4Tracker()
        cik, name = tracker.lookup_ticker('INVALID')
        
        assert cik is None
        assert name is None
    
    def test_abbreviate_role(self, mock_env_vars, temp_dir, sample_company_tickers, monkeypatch):
        """Test role abbreviation."""
        from services.form4_company import CompanyForm4Tracker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        tracker = CompanyForm4Tracker()
        
        assert tracker.abbreviate_role('Chief Executive Officer') == 'CEO'
        assert tracker.abbreviate_role('Director') == 'Dir'
    
    def test_format_amount(self, mock_env_vars, temp_dir, sample_company_tickers, monkeypatch):
        """Test amount formatting."""
        from services.form4_company import CompanyForm4Tracker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        tracker = CompanyForm4Tracker()
        
        assert '$1.0M' in tracker.format_amount(1_000_000) or '$1M' in tracker.format_amount(1_000_000)
        assert '$1K' in tracker.format_amount(1_000) or '$1.0K' in tracker.format_amount(1_000)
    
    def test_format_transaction(self, mock_env_vars, temp_dir, sample_company_tickers, sample_form4_transaction, monkeypatch):
        """Test transaction formatting."""
        from services.form4_company import CompanyForm4Tracker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        tracker = CompanyForm4Tracker()
        formatted = tracker.format_transaction(sample_form4_transaction)
        
        assert 'BUY' in formatted
        assert '1,000' in formatted or '1000' in formatted
    
    def test_get_form4_cache_dir(self, mock_env_vars, temp_dir, sample_company_tickers, monkeypatch):
        """Test cache directory creation."""
        from services.form4_company import CompanyForm4Tracker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        tracker = CompanyForm4Tracker()
        cache_dir = tracker.get_form4_cache_dir()
        
        assert Path(cache_dir).exists()
    
    def test_save_and_load_form4_cache(self, mock_env_vars, temp_dir, sample_company_tickers, sample_form4_transaction, monkeypatch):
        """Test saving and loading Form 4 cache."""
        from services.form4_company import CompanyForm4Tracker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        tracker = CompanyForm4Tracker()
        
        # Save transactions
        transactions = [sample_form4_transaction]
        tracker.save_form4_cache('AAPL', transactions)
        
        # Load transactions
        loaded = tracker.load_form4_cache('AAPL')
        
        assert loaded is not None
        assert 'transactions' in loaded
        assert len(loaded['transactions']) == 1
    
    def test_is_form4_cache_valid(self, mock_env_vars, temp_dir, sample_company_tickers, sample_form4_transaction, monkeypatch):
        """Test cache validity checking."""
        from services.form4_company import CompanyForm4Tracker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        tracker = CompanyForm4Tracker()
        
        # No cache - should be invalid
        assert tracker.is_form4_cache_valid('AAPL') is False
        
        # Create cache
        tracker.save_form4_cache('AAPL', [sample_form4_transaction])
        
        # Fresh cache - should be valid
        assert tracker.is_form4_cache_valid('AAPL') is True


class TestParseDateRange:
    """Tests for parse_date_range function."""
    
    def test_parse_simple_date_range(self, mock_env_vars):
        """Test parsing simple date range."""
        from services.form4_company import parse_date_range
        
        start, end = parse_date_range('7/1 - 7/31')
        
        assert start.month == 7
        assert start.day == 1
        assert end.month == 7
        assert end.day == 31
    
    def test_parse_date_range_with_year(self, mock_env_vars):
        """Test parsing date range with year."""
        from services.form4_company import parse_date_range
        
        start, end = parse_date_range('1/1/25 - 1/31/25')
        
        assert start.year == 2025
        assert start.month == 1
        assert start.day == 1
        assert end.year == 2025
        assert end.month == 1
        assert end.day == 31
    
    def test_parse_date_range_year_boundary(self, mock_env_vars):
        """Test parsing date range across year boundary."""
        from services.form4_company import parse_date_range
        
        # December to January should handle year correctly
        start, end = parse_date_range('12/28 - 1/5')
        
        # End should be next year if it comes before start
        if end < start:
            assert end.year == start.year + 1


class TestParseArgs:
    """Tests for parse_args function."""
    
    def test_parse_single_ticker(self, mock_env_vars, monkeypatch):
        """Test parsing single ticker."""
        from services.form4_company import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_company.py', 'AAPL'])
        
        tickers, count, hide_planned, days_back, date_range = parse_args()
        
        assert 'AAPL' in tickers
    
    def test_parse_multiple_tickers(self, mock_env_vars, monkeypatch):
        """Test parsing multiple tickers."""
        from services.form4_company import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_company.py', 'AAPL', 'NVDA', 'TSLA'])
        
        tickers, count, hide_planned, days_back, date_range = parse_args()
        
        assert 'AAPL' in tickers
        assert 'NVDA' in tickers
        assert 'TSLA' in tickers
    
    def test_parse_with_count_flag(self, mock_env_vars, monkeypatch):
        """Test parsing with -r count flag."""
        from services.form4_company import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_company.py', 'AAPL', '-r', '20'])
        
        tickers, count, hide_planned, days_back, date_range = parse_args()
        
        assert count == 20
    
    def test_parse_with_hide_planned_flag(self, mock_env_vars, monkeypatch):
        """Test parsing with -hp hide planned flag."""
        from services.form4_company import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_company.py', 'AAPL', '-hp'])
        
        tickers, count, hide_planned, days_back, date_range = parse_args()
        
        assert hide_planned is True
    
    def test_parse_with_days_back_flag(self, mock_env_vars, monkeypatch):
        """Test parsing with -d days flag."""
        from services.form4_company import parse_args
        
        monkeypatch.setattr('sys.argv', ['form4_company.py', 'AAPL', '-d', '60'])
        
        tickers, count, hide_planned, days_back, date_range = parse_args()
        
        assert days_back == 60


class TestGroupTransactionsByPerson:
    """Tests for group_transactions_by_person function."""
    
    def test_group_single_person(self, mock_env_vars, sample_form4_transaction):
        """Test grouping transactions for single person."""
        from services.form4_company import group_transactions_by_person
        
        transactions = [sample_form4_transaction]
        grouped = group_transactions_by_person(transactions)
        
        assert len(grouped) == 1
        key = list(grouped.keys())[0]
        assert 'John Doe' in key
    
    def test_group_multiple_persons(self, mock_env_vars, sample_form4_transaction):
        """Test grouping transactions for multiple persons."""
        from services.form4_company import group_transactions_by_person
        
        trans1 = sample_form4_transaction.copy()
        trans2 = sample_form4_transaction.copy()
        trans2['owner_name'] = 'Jane Smith'
        
        transactions = [trans1, trans2]
        grouped = group_transactions_by_person(transactions)
        
        assert len(grouped) == 2


class TestHasPlannedTransactions:
    """Tests for has_planned_transactions function."""
    
    def test_has_planned_true(self, mock_env_vars, sample_form4_transaction):
        """Test detecting planned transactions."""
        from services.form4_company import has_planned_transactions
        
        trans = sample_form4_transaction.copy()
        trans['planned'] = True
        
        assert has_planned_transactions([trans]) is True
    
    def test_has_planned_false(self, mock_env_vars, sample_form4_transaction):
        """Test detecting no planned transactions."""
        from services.form4_company import has_planned_transactions
        
        trans = sample_form4_transaction.copy()
        trans['planned'] = False
        
        assert has_planned_transactions([trans]) is False


class TestForm4CompanyEdgeCases:
    """Tests for edge cases in Form 4 company tracking."""
    
    def test_handles_no_transactions(self, mock_env_vars, temp_dir, sample_company_tickers, monkeypatch, capsys):
        """Test handling when no transactions found."""
        from services.form4_company import display_single_company, CompanyForm4Tracker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        tracker = CompanyForm4Tracker()
        display_single_company(tracker, 'AAPL', [])
        
        captured = capsys.readouterr()
        assert 'No transactions found' in captured.out
    
    def test_handles_empty_cache(self, mock_env_vars, temp_dir, sample_company_tickers, monkeypatch):
        """Test handling empty cache."""
        from services.form4_company import CompanyForm4Tracker
        
        monkeypatch.chdir(temp_dir)
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps(sample_company_tickers))
        
        tracker = CompanyForm4Tracker()
        
        loaded = tracker.load_form4_cache('NONEXISTENT')
        assert loaded is None
