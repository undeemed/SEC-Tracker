"""
Extended tests for core/tracker.py - Additional coverage for main functions.
"""

import pytest
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFilingTrackerExtended:
    """Extended tests for FilingTracker class."""
    
    def test_tracker_initialization(self, temp_dir, mock_env_vars, monkeypatch):
        """Test tracker initialization."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        # Create ticker cache
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text(json.dumps({
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }))
        
        tracker = FilingTracker()
        
        assert tracker is not None
    
    def test_is_new_filing(self, temp_dir, mock_env_vars, monkeypatch):
        """Test checking for new filings."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        # Create tracker with empty state
        tracker = FilingTracker()
        
        # New filings should be detected
        assert tracker.is_new_filing("0001234-25-000001")
    
    def test_mark_filing_downloaded(self, temp_dir, mock_env_vars, monkeypatch):
        """Test marking filing as downloaded."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        tracker = FilingTracker()
        
        # Create a filing dict
        filing = {
            "accession": "0001234-25-000001",
            "form": "10-K",
            "filing_date": "2025-01-15",
            "doc_url": "https://example.com/filing.htm"
        }
        
        tracker.mark_filing_downloaded(filing)
        
        assert not tracker.is_new_filing("0001234-25-000001")


class TestTrackerMain:
    """Tests for tracker main function."""
    
    def test_main_list_companies(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test main with --list-companies flag."""
        from core.tracker import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['tracker.py', '--list-companies'])
        
        # Create state with companies
        state = {
            "last_check": datetime.now().isoformat(),
            "filings": {},
            "analyzed": {},
            "companies": {"AAPL": {"ticker": "AAPL"}}
        }
        (temp_dir / 'filing_state.json').write_text(json.dumps(state))
        
        main()
        
        captured = capsys.readouterr()
        assert "AAPL" in captured.out or "Tracked" in captured.out


class TestExtractSentimentFromText:
    """Tests for extract_sentiment_from_text function."""
    
    def test_extract_basic_sentiment(self, mock_env_vars):
        """Test basic sentiment extraction."""
        from core.tracker import extract_sentiment_from_text
        
        text = "Revenue increased 25% year over year. Strong growth momentum."
        result = extract_sentiment_from_text(text, "10-K")
        
        assert isinstance(result, dict)
        assert 'key_info' in result
    
    def test_extract_negative_sentiment(self, mock_env_vars):
        """Test negative sentiment extraction."""
        from core.tracker import extract_sentiment_from_text
        
        text = "Revenue decreased. Loss reported. Risk factors increased."
        result = extract_sentiment_from_text(text, "10-K")
        
        assert isinstance(result, dict)


class TestPrintSummary:
    """Tests for print_summary function."""
    
    def test_print_summary(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test print_summary function."""
        from core.tracker import print_summary
        
        monkeypatch.chdir(temp_dir)
        
        state = {
            "last_check": datetime.now().isoformat(),
            "filings": {
                "test1": {"form": "10-K", "filing_date": "2025-01-10", "downloaded_at": datetime.now().isoformat()},
            },
            "analyzed": {},
            "companies": {}
        }
        (temp_dir / 'filing_state.json').write_text(json.dumps(state))
        
        print_summary()
        
        captured = capsys.readouterr()
        assert "SEC Filing Tracker Summary" in captured.out or "Summary" in captured.out
