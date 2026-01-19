"""
Extended tests for core/downloader.py - Additional coverage.
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDownloadCompanyFilings:
    """Extended tests for download_company_filings function."""
    
    def test_download_basic(self, temp_dir, mock_env_vars, sample_company_tickers, monkeypatch):
        """Test basic download function."""
        # This test verifies the download module can be imported and functions exist
        from core.downloader import download_company_filings
        
        assert callable(download_company_filings)


class TestDownloadAll:
    """Tests for download_all function."""
    
    def test_download_all_exists(self, mock_env_vars):
        """Test download_all function exists."""
        from core.downloader import download_all
        
        assert callable(download_all)


class TestDownloaderMain:
    """Tests for downloader main function."""
    
    def test_main_exists(self, mock_env_vars):
        """Test main function exists."""
        from core.downloader import main
        
        assert callable(main)
