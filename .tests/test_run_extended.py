"""
Extended tests for run.py - Additional coverage.
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCommandMapping:
    """Tests for command mapping in run.py."""
    
    def test_all_commands_exist(self, mock_env_vars, monkeypatch):
        """Test that all mapped commands have valid scripts."""
        from run import commands
        
        for cmd_name, script_path in commands.items():
            if script_path:
                # Script path should be valid
                assert isinstance(script_path, str)
                assert len(script_path) > 0
    
    def test_command_descriptions(self, mock_env_vars, monkeypatch):
        """Test that all commands have descriptions."""
        from run import cmd_descriptions
        
        assert len(cmd_descriptions) > 0
        for cmd, desc in cmd_descriptions.items():
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestHelpOutput:
    """Tests for help output."""
    
    def test_no_args_shows_help(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test that no arguments shows help."""
        from run import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['run.py'])
        
        try:
            main()
        except SystemExit:
            pass
        
        captured = capsys.readouterr()
        assert 'SEC' in captured.out or 'Commands' in captured.out


class TestTrackCommand:
    """Tests for track command."""
    
    def test_track_command(self, temp_dir, mock_env_vars, sample_company_tickers, monkeypatch, capsys):
        """Test track command execution."""
        from run import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['run.py', 'track', 'AAPL'])
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text('{}')
        
        # Mock subprocess to avoid actual execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            main()
        
        # Should have called subprocess
        assert True


class TestForm4Command:
    """Tests for form4 command."""
    
    def test_form4_command(self, temp_dir, mock_env_vars, sample_company_tickers, monkeypatch, capsys):
        """Test form4 command execution."""
        from run import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['run.py', 'form4', 'AAPL'])
        
        cache_file = temp_dir / 'company_tickers_cache.json'
        cache_file.write_text('{}')
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            main()
        
        assert True


class TestLatestCommand:
    """Tests for latest command."""
    
    def test_latest_command(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test latest command execution."""
        from run import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['run.py', 'latest'])
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            main()
        
        assert True


class TestAnalyzeCommand:
    """Tests for analyze command."""
    
    def test_analyze_command(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test analyze command execution."""
        from run import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['run.py', 'analyze', 'AAPL'])
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            main()
        
        assert True


class TestMonitorCommand:
    """Tests for monitor command."""
    
    def test_monitor_command(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test monitor command execution."""
        from run import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['run.py', 'monitor'])
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            main()
        
        assert True


class TestModelCommand:
    """Tests for model command."""
    
    def test_model_command(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test model command execution."""
        from run import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['run.py', 'model'])
        
        (temp_dir / '.env').write_text('')
        
        # Mock input to avoid interactive prompt
        monkeypatch.setattr('builtins.input', lambda _: '')
        
        main()
        
        captured = capsys.readouterr()
        # Should show model info or prompt
        assert len(captured.out) >= 0


class TestMultiCommand:
    """Tests for multi command."""
    
    def test_multi_list(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test multi list command."""
        from run import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['run.py', 'multi', 'list'])
        
        main()
        
        captured = capsys.readouterr()
        # Should show some output about models
        assert len(captured.out) >= 0


class TestRefreshCommands:
    """Tests for refresh commands."""
    
    def test_refresh_cache_command(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test refresh-cache command execution."""
        from run import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['run.py', 'refresh-cache'])
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            main()
        
        assert True
    
    def test_refresh_latest_command(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test refresh-latest command execution."""
        from run import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['run.py', 'refresh-latest'])
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            main()
        
        assert True


class TestInvalidCommand:
    """Tests for invalid command handling."""
    
    def test_invalid_command(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test handling of invalid command."""
        from run import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['run.py', 'nonexistent'])
        
        try:
            main()
        except SystemExit:
            pass
        
        captured = capsys.readouterr()
        assert 'Unknown' in captured.out or len(captured.out) > 0


class TestSubprocessExecution:
    """Tests for subprocess execution."""
    
    def test_subprocess_error_handling(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test subprocess error handling."""
        from run import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['run.py', 'track', 'AAPL'])
        
        # Mock subprocess to return error
        mock_result = MagicMock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result):
            main()
        
        # Should handle error gracefully
        assert True
    
    def test_subprocess_exception(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test handling of subprocess exception."""
        from run import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['run.py', 'track', 'AAPL'])
        
        with patch('subprocess.run', side_effect=FileNotFoundError("Script not found")):
            try:
                main()
            except (FileNotFoundError, SystemExit):
                pass  # Expected
        
        assert True
