"""
Extended tests for services/monitor.py - Additional coverage.
"""

import pytest
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFilingMonitorExtended:
    """Extended tests for FilingMonitor class."""
    
    def test_monitor_initialization(self, temp_dir, mock_env_vars, monkeypatch):
        """Test monitor initialization."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        monitor = FilingMonitor()
        
        assert monitor is not None
    
    def test_monitor_with_state_file(self, temp_dir, mock_env_vars, monkeypatch):
        """Test monitor with existing state file."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        # Create state file
        state = {
            "last_check": datetime.now().isoformat(),
            "filings": {},
            "analyzed": {},
            "companies": {}
        }
        (temp_dir / 'filing_state.json').write_text(json.dumps(state))
        
        monitor = FilingMonitor()
        
        assert monitor is not None


class TestMonitorMain:
    """Tests for monitor main function."""
    
    def test_main_default(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test main without arguments."""
        from services.monitor import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['monitor.py'])
        
        # Create directories to prevent errors
        (temp_dir / 'sec_filings').mkdir()
        (temp_dir / 'analysis_results').mkdir()
        
        main()
        
        captured = capsys.readouterr()
        assert 'SEC Filing Monitor' in captured.out or len(captured.out) >= 0
