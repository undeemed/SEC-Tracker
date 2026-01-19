"""
Tests for scripts/refresh_cache.py and scripts/refresh_latest.py
"""

import pytest
import json
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRefreshGlobalLatestCache:
    """Tests for refresh_global_latest_cache function."""
    
    def test_no_cache_exists(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test when no global cache exists."""
        from scripts.refresh_cache import refresh_global_latest_cache
        
        monkeypatch.chdir(temp_dir)
        
        result = refresh_global_latest_cache()
        
        assert result is False
        captured = capsys.readouterr()
        assert "No global latest filings cache found" in captured.out
    
    def test_cache_refresh_success(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test successful cache refresh."""
        from scripts.refresh_cache import refresh_global_latest_cache
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache file
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "form4_filings_cache.json"
        cache_file.write_text('{"test": "data"}')
        
        # Mock subprocess.run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            result = refresh_global_latest_cache()
        
        assert result is True
        captured = capsys.readouterr()
        assert "Successfully refreshed" in captured.out
    
    def test_cache_refresh_failure(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test failed cache refresh."""
        from scripts.refresh_cache import refresh_global_latest_cache
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache file
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "form4_filings_cache.json"
        cache_file.write_text('{"test": "data"}')
        
        # Mock subprocess.run with failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error occurred"
        
        with patch('subprocess.run', return_value=mock_result):
            result = refresh_global_latest_cache()
        
        assert result is False
        captured = capsys.readouterr()
        assert "Failed to refresh" in captured.out
    
    def test_cache_refresh_timeout(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test timeout during cache refresh."""
        from scripts.refresh_cache import refresh_global_latest_cache
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache file
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "form4_filings_cache.json"
        cache_file.write_text('{"test": "data"}')
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 120)):
            result = refresh_global_latest_cache()
        
        assert result is False
        captured = capsys.readouterr()
        assert "Timeout" in captured.out
    
    def test_cache_refresh_exception(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test general exception during cache refresh."""
        from scripts.refresh_cache import refresh_global_latest_cache
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache file
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "form4_filings_cache.json"
        cache_file.write_text('{"test": "data"}')
        
        with patch('subprocess.run', side_effect=Exception("Unexpected error")):
            result = refresh_global_latest_cache()
        
        assert result is False
        captured = capsys.readouterr()
        assert "Error" in captured.out


class TestRefreshAllForm4Caches:
    """Tests for refresh_all_form4_caches function."""
    
    def test_no_cache_dir(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test when no Form 4 cache directory exists."""
        from scripts.refresh_cache import refresh_all_form4_caches
        
        monkeypatch.chdir(temp_dir)
        
        refresh_all_form4_caches()
        
        captured = capsys.readouterr()
        assert "No Form 4 cache directory found" in captured.out
    
    def test_no_cache_files(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test when cache directory exists but no files."""
        from scripts.refresh_cache import refresh_all_form4_caches
        
        monkeypatch.chdir(temp_dir)
        
        # Create empty cache directory
        cache_dir = temp_dir / "cache" / "form4_track"
        cache_dir.mkdir(parents=True)
        
        refresh_all_form4_caches()
        
        captured = capsys.readouterr()
        assert "No Form 4 cache files found" in captured.out
    
    def test_refresh_multiple_caches(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test refreshing multiple cache files."""
        from scripts.refresh_cache import refresh_all_form4_caches
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache directory with files
        cache_dir = temp_dir / "cache" / "form4_track"
        cache_dir.mkdir(parents=True)
        
        (cache_dir / "AAPL_form4_cache.json").write_text('{"ticker": "AAPL"}')
        (cache_dir / "NVDA_form4_cache.json").write_text('{"ticker": "NVDA"}')
        
        # Mock subprocess.run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            refresh_all_form4_caches()
        
        captured = capsys.readouterr()
        assert "Found 2 Form 4 cache files" in captured.out
        assert "AAPL" in captured.out
        assert "NVDA" in captured.out
        assert "Cache refresh complete" in captured.out
    
    def test_refresh_with_failures(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test refreshing with some failures."""
        from scripts.refresh_cache import refresh_all_form4_caches
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache directory with files
        cache_dir = temp_dir / "cache" / "form4_track"
        cache_dir.mkdir(parents=True)
        
        (cache_dir / "AAPL_form4_cache.json").write_text('{"ticker": "AAPL"}')
        
        # Mock subprocess.run with failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Failed"
        
        with patch('subprocess.run', return_value=mock_result):
            refresh_all_form4_caches()
        
        captured = capsys.readouterr()
        assert "Failed to refresh AAPL" in captured.out
    
    def test_refresh_with_timeout(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test refreshing with timeout."""
        from scripts.refresh_cache import refresh_all_form4_caches
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache directory with files
        cache_dir = temp_dir / "cache" / "form4_track"
        cache_dir.mkdir(parents=True)
        
        (cache_dir / "AAPL_form4_cache.json").write_text('{"ticker": "AAPL"}')
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 60)):
            refresh_all_form4_caches()
        
        captured = capsys.readouterr()
        assert "Timeout refreshing AAPL" in captured.out
    
    def test_delete_failure(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test when file deletion fails."""
        from scripts.refresh_cache import refresh_all_form4_caches
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache directory with files
        cache_dir = temp_dir / "cache" / "form4_track"
        cache_dir.mkdir(parents=True)
        
        cache_file = cache_dir / "AAPL_form4_cache.json"
        cache_file.write_text('{"ticker": "AAPL"}')
        
        # Mock unlink to raise exception
        with patch.object(Path, 'unlink', side_effect=PermissionError("Permission denied")):
            refresh_all_form4_caches()
        
        captured = capsys.readouterr()
        assert "Failed to delete" in captured.out


class TestRefreshCacheMain:
    """Tests for refresh_cache main function."""
    
    def test_main_help(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test main with --help flag."""
        from scripts.refresh_cache import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['refresh_cache.py', '--help'])
        
        main()
        
        captured = capsys.readouterr()
        assert "Refresh all existing Form 4 caches" in captured.out
    
    def test_main_default(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test main without arguments."""
        from scripts.refresh_cache import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['refresh_cache.py'])
        
        main()
        
        captured = capsys.readouterr()
        assert "No Form 4 cache directory found" in captured.out


class TestRefreshLatestCache:
    """Tests for scripts/refresh_latest.py"""
    
    def test_no_cache_exists(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test when no cache exists."""
        from scripts.refresh_latest import refresh_latest_cache
        
        monkeypatch.chdir(temp_dir)
        
        result = refresh_latest_cache()
        
        assert result is False
        captured = capsys.readouterr()
        assert "No global latest filings cache found" in captured.out
    
    def test_cache_refresh_success(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test successful cache refresh."""
        from scripts.refresh_latest import refresh_latest_cache
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache file
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "form4_filings_cache.json"
        cache_file.write_text('{"test": "data"}')
        
        # Mock subprocess.run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            result = refresh_latest_cache()
        
        assert result is True
        captured = capsys.readouterr()
        assert "Successfully refreshed" in captured.out
    
    def test_cache_refresh_failure(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test failed cache refresh."""
        from scripts.refresh_latest import refresh_latest_cache
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache file
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "form4_filings_cache.json"
        cache_file.write_text('{"test": "data"}')
        
        # Mock subprocess.run with failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error occurred"
        
        with patch('subprocess.run', return_value=mock_result):
            result = refresh_latest_cache()
        
        assert result is False
        captured = capsys.readouterr()
        assert "Failed to refresh" in captured.out
    
    def test_cache_refresh_timeout(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test timeout during cache refresh."""
        from scripts.refresh_latest import refresh_latest_cache
        
        monkeypatch.chdir(temp_dir)
        
        # Create cache file
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "form4_filings_cache.json"
        cache_file.write_text('{"test": "data"}')
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 120)):
            result = refresh_latest_cache()
        
        assert result is False
        captured = capsys.readouterr()
        assert "Timeout" in captured.out


class TestRefreshLatestMain:
    """Tests for refresh_latest main function."""
    
    def test_main_help(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test main with --help flag."""
        from scripts.refresh_latest import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['refresh_latest.py', '--help'])
        
        main()
        
        captured = capsys.readouterr()
        assert "Refresh the global latest filings cache" in captured.out
    
    def test_main_success(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test main with successful refresh."""
        from scripts.refresh_latest import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['refresh_latest.py'])
        
        # Create cache file
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "form4_filings_cache.json"
        cache_file.write_text('{"test": "data"}')
        
        # Mock subprocess.run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            main()
        
        captured = capsys.readouterr()
        assert "refresh complete" in captured.out
    
    def test_main_failure(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test main with failed refresh."""
        from scripts.refresh_latest import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['refresh_latest.py'])
        
        # Create cache file
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        cache_file = cache_dir / "form4_filings_cache.json"
        cache_file.write_text('{"test": "data"}')
        
        # Mock subprocess.run with failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error"
        
        with patch('subprocess.run', return_value=mock_result):
            with pytest.raises(SystemExit) as exc_info:
                main()
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "failed" in captured.out
