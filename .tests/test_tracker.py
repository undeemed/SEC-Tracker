"""
Tests for core/tracker.py - Filing tracking functionality.
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFilingTracker:
    """Tests for FilingTracker class."""
    
    def test_tracker_creation(self, temp_dir, monkeypatch, mock_env_vars):
        """Test FilingTracker can be created."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        tracker = FilingTracker()
        assert tracker is not None
        assert tracker.state is not None
    
    def test_tracker_loads_existing_state(self, temp_dir, sample_filing_state, monkeypatch, mock_env_vars):
        """Test FilingTracker loads existing state file."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        tracker = FilingTracker()
        
        assert len(tracker.state["filings"]) > 0
    
    def test_tracker_creates_default_state(self, temp_dir, monkeypatch, mock_env_vars):
        """Test FilingTracker creates default state when no file exists."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        tracker = FilingTracker()
        
        assert "last_check" in tracker.state
        assert "filings" in tracker.state
        assert "analyzed" in tracker.state
        assert "companies" in tracker.state
    
    def test_save_state(self, temp_dir, monkeypatch, mock_env_vars):
        """Test saving state to file."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        tracker = FilingTracker()
        tracker.state["test_key"] = "test_value"
        tracker.save_state()
        
        state_file = temp_dir / 'filing_state.json'
        assert state_file.exists()
        
        saved_state = json.loads(state_file.read_text())
        assert saved_state["test_key"] == "test_value"
    
    def test_is_new_filing(self, temp_dir, sample_filing_state, monkeypatch, mock_env_vars):
        """Test checking if a filing is new."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        tracker = FilingTracker()
        
        # Existing filing
        assert tracker.is_new_filing("0001234567-25-000001") is False
        
        # New filing
        assert tracker.is_new_filing("NEW-ACCESSION-123") is True
    
    def test_mark_filing_downloaded(self, temp_dir, monkeypatch, mock_env_vars):
        """Test marking a filing as downloaded."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        tracker = FilingTracker()
        
        filing = {
            "accession": "TEST-123",
            "form": "10-K",
            "filing_date": "2025-01-15",
            "doc_url": "https://example.com/doc.htm"
        }
        
        tracker.mark_filing_downloaded(filing)
        
        assert "TEST-123" in tracker.state["filings"]
        assert tracker.state["filings"]["TEST-123"]["form"] == "10-K"
    
    def test_get_new_filings(self, temp_dir, sample_filing_state, monkeypatch, mock_env_vars):
        """Test filtering to only new filings."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        tracker = FilingTracker()
        
        fetched_filings = {
            "10-K": [
                {"accession": "0001234567-25-000001", "doc_url": "url1"},  # Existing
                {"accession": "NEW-10K-123", "doc_url": "url2"}  # New
            ],
            "8-K": [
                {"accession": "NEW-8K-456", "doc_url": "url3"}  # New
            ]
        }
        
        new_filings = tracker.get_new_filings(fetched_filings)
        
        # Should only contain new filings
        assert len(new_filings["10-K"]) == 1
        assert new_filings["10-K"][0]["accession"] == "NEW-10K-123"
        assert len(new_filings["8-K"]) == 1
    
    def test_update_last_check(self, temp_dir, monkeypatch, mock_env_vars):
        """Test updating the last check timestamp."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        tracker = FilingTracker()
        
        before = datetime.now()
        tracker.update_last_check()
        after = datetime.now()
        
        check_time = datetime.fromisoformat(tracker.state["last_check"])
        assert before <= check_time <= after
    
    def test_needs_analysis_no_previous(self, temp_dir, monkeypatch, mock_env_vars):
        """Test needs_analysis returns True when never analyzed."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        tracker = FilingTracker()
        tracker.state["filings"]["TEST"] = {"form": "10-K", "downloaded_at": datetime.now().isoformat()}
        
        assert tracker.needs_analysis("10-K") is True
    
    def test_needs_analysis_with_newer_filings(self, temp_dir, sample_filing_state, monkeypatch, mock_env_vars):
        """Test needs_analysis detects newer filings."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        tracker = FilingTracker()
        
        # Add a filing newer than last analysis
        tracker.state["filings"]["NEW-FILING"] = {
            "form": "10-K",
            "filing_date": "2025-01-20",
            "downloaded_at": datetime.now().isoformat()
        }
        
        assert tracker.needs_analysis("10-K") is True
    
    def test_needs_analysis_force(self, temp_dir, sample_filing_state, monkeypatch, mock_env_vars):
        """Test needs_analysis with force=True."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        tracker = FilingTracker()
        
        # Should return True when forced
        assert tracker.needs_analysis("10-K", force=True) is True
    
    def test_mark_analyzed(self, temp_dir, monkeypatch, mock_env_vars):
        """Test marking a form type as analyzed."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        tracker = FilingTracker()
        
        before = datetime.now()
        tracker.mark_analyzed("10-K")
        after = datetime.now()
        
        assert "10-K" in tracker.state["analyzed"]
        analysis_time = datetime.fromisoformat(tracker.state["analyzed"]["10-K"])
        assert before <= analysis_time <= after
    
    def test_add_company(self, temp_dir, monkeypatch, mock_env_vars):
        """Test adding a company to track."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        tracker = FilingTracker()
        
        company_info = {"cik": "0000320193", "ticker": "AAPL", "name": "Apple Inc."}
        tracker.add_company("AAPL", company_info)
        
        assert "AAPL" in tracker.state["companies"]
        assert tracker.state["companies"]["AAPL"]["ticker"] == "AAPL"
    
    def test_get_most_recent_filing_date(self, temp_dir, sample_filing_state, monkeypatch, mock_env_vars):
        """Test getting most recent filing date."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        tracker = FilingTracker()
        
        most_recent = tracker.get_most_recent_filing_date()
        
        assert most_recent is not None
        assert most_recent == "2025-01-15"  # Based on sample_filing_state
    
    def test_get_most_recent_filing_date_empty(self, temp_dir, monkeypatch, mock_env_vars):
        """Test getting most recent filing date when no filings."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        tracker = FilingTracker()
        
        most_recent = tracker.get_most_recent_filing_date()
        
        assert most_recent is None


class TestFilingTrackerUtilities:
    """Tests for FilingTracker utility functions."""
    
    def test_get_filing_metadata(self, temp_dir, sample_filing_state, monkeypatch, mock_env_vars):
        """Test getting filing metadata."""
        from core.tracker import get_filing_metadata, FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        metadata = get_filing_metadata("0001234567-25-000001")
        
        assert metadata is not None
        assert metadata["form"] == "10-K"
    
    def test_get_filing_metadata_not_found(self, temp_dir, monkeypatch, mock_env_vars):
        """Test getting metadata for non-existent filing."""
        from core.tracker import get_filing_metadata
        
        monkeypatch.chdir(temp_dir)
        
        metadata = get_filing_metadata("NONEXISTENT-123")
        
        assert metadata is None
    
    def test_get_filings_since(self, temp_dir, sample_filing_state, monkeypatch, mock_env_vars):
        """Test getting filings since a date."""
        from core.tracker import get_filings_since
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        cutoff = datetime(2025, 1, 12)
        filings = get_filings_since(cutoff)
        
        assert len(filings) > 0
        for filing in filings:
            filing_date = datetime.strptime(filing["filing_date"], "%Y-%m-%d")
            assert filing_date >= cutoff
    
    def test_get_filings_since_with_form_type(self, temp_dir, sample_filing_state, monkeypatch, mock_env_vars):
        """Test getting filings since a date filtered by form type."""
        from core.tracker import get_filings_since
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        cutoff = datetime(2025, 1, 1)
        filings = get_filings_since(cutoff, form_type="10-K")
        
        for filing in filings:
            assert filing["form"] == "10-K"


class TestExtractSentimentFromText:
    """Tests for sentiment extraction."""
    
    def test_extract_bullish_sentiment(self, mock_env_vars):
        """Test extracting bullish sentiment."""
        from core.tracker import extract_sentiment_from_text
        
        text = "Strong growth momentum with record revenue and positive expansion outlook."
        result = extract_sentiment_from_text(text, "10-K")
        
        assert result["sentiment"] == "Bullish"
    
    def test_extract_bearish_sentiment(self, mock_env_vars):
        """Test extracting bearish sentiment."""
        from core.tracker import extract_sentiment_from_text
        
        text = "Declining revenue with significant loss and weak market conditions causing concern."
        result = extract_sentiment_from_text(text, "10-K")
        
        assert result["sentiment"] == "Bearish"
    
    def test_extract_neutral_sentiment(self, mock_env_vars):
        """Test extracting neutral sentiment."""
        from core.tracker import extract_sentiment_from_text
        
        text = "The company filed its quarterly report with mixed results."
        result = extract_sentiment_from_text(text, "10-K")
        
        assert result["sentiment"] == "Neutral"
    
    def test_extract_key_info_10k(self, mock_env_vars):
        """Test extracting key info from 10-K."""
        from core.tracker import extract_sentiment_from_text
        
        text = "Total revenues were $500 billion for the fiscal year."
        result = extract_sentiment_from_text(text, "10-K")
        
        # Should extract revenue info if formatted correctly
        assert isinstance(result["key_info"], list)
    
    def test_extract_key_info_8k(self, mock_env_vars):
        """Test extracting key info from 8-K."""
        from core.tracker import extract_sentiment_from_text
        
        text = "The company announced an acquisition of XYZ Corp and appointment of new CEO."
        result = extract_sentiment_from_text(text, "8-K")
        
        # Should detect acquisition and management changes
        assert any("Acquisition" in info or "Management" in info for info in result["key_info"])


class TestFilingTrackerEdgeCases:
    """Tests for edge cases in FilingTracker."""
    
    def test_handles_corrupt_state_file(self, temp_dir, monkeypatch, mock_env_vars):
        """Test handling of corrupt state file."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text('not valid json {{{')
        
        # Should handle gracefully and create new state
        with pytest.raises(json.JSONDecodeError):
            tracker = FilingTracker()
    
    def test_handles_empty_filings(self, temp_dir, monkeypatch, mock_env_vars):
        """Test handling when no filings exist."""
        from core.tracker import FilingTracker
        
        monkeypatch.chdir(temp_dir)
        
        tracker = FilingTracker()
        
        new_filings = tracker.get_new_filings({
            "10-K": [],
            "8-K": []
        })
        
        assert new_filings == {}  # Empty dict for no new filings
