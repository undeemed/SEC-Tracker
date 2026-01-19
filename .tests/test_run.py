"""
Tests for run.py - CLI entry point.
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCommandMapping:
    """Tests for command mapping in run.py."""
    
    def test_commands_defined(self, mock_env_vars):
        """Test that commands dictionary is defined."""
        from run import commands
        
        assert isinstance(commands, dict)
        assert len(commands) > 0
    
    def test_core_commands_exist(self, mock_env_vars):
        """Test that core commands are mapped."""
        from run import commands
        
        assert 'scan' in commands
        assert 'fetch' in commands
        assert 'download' in commands
        assert 'track' in commands
        assert 'analyze' in commands
    
    def test_service_commands_exist(self, mock_env_vars):
        """Test that service commands are mapped."""
        from run import commands
        
        assert 'form4' in commands
        assert 'latest' in commands
        assert 'monitor' in commands
    
    def test_utility_commands_exist(self, mock_env_vars):
        """Test that utility commands are mapped."""
        from run import commands
        
        assert 'update-key' in commands
        assert 'refresh-cache' in commands
        assert 'refresh-latest' in commands
    
    def test_command_paths_valid(self, mock_env_vars):
        """Test that command paths point to existing files."""
        from run import commands
        
        project_root = Path(__file__).parent.parent
        
        for cmd, path in commands.items():
            full_path = project_root / path
            assert full_path.exists(), f"Command '{cmd}' points to non-existent file: {path}"


class TestCommandDescriptions:
    """Tests for command descriptions."""
    
    def test_descriptions_defined(self, mock_env_vars):
        """Test that descriptions dictionary is defined."""
        from run import cmd_descriptions
        
        assert isinstance(cmd_descriptions, dict)
        assert len(cmd_descriptions) > 0
    
    def test_all_commands_have_descriptions(self, mock_env_vars):
        """Test that all commands have descriptions."""
        from run import commands, cmd_descriptions
        
        for cmd in commands:
            assert cmd in cmd_descriptions, f"Command '{cmd}' missing description"


class TestPrintHelp:
    """Tests for print_help function."""
    
    def test_print_help_outputs(self, mock_env_vars, capsys):
        """Test that print_help produces output."""
        from run import print_help
        
        print_help()
        
        captured = capsys.readouterr()
        assert 'SEC Filing Tracker' in captured.out
        assert 'Available Commands' in captured.out
    
    def test_print_help_shows_examples(self, mock_env_vars, capsys):
        """Test that help shows usage examples."""
        from run import print_help
        
        print_help()
        
        captured = capsys.readouterr()
        assert 'Examples:' in captured.out
        assert 'python run.py' in captured.out
    
    def test_print_help_shows_core_commands(self, mock_env_vars, capsys):
        """Test that help shows core commands."""
        from run import print_help
        
        print_help()
        
        captured = capsys.readouterr()
        assert 'track' in captured.out
        assert 'analyze' in captured.out
    
    def test_print_help_shows_model_commands(self, mock_env_vars, capsys):
        """Test that help shows model management commands."""
        from run import print_help
        
        print_help()
        
        captured = capsys.readouterr()
        assert 'model' in captured.out
        assert '-switch' in captured.out


class TestHandleModelCommand:
    """Tests for handle_model_command function."""
    
    def test_model_no_args_shows_current(self, mock_env_vars, capsys):
        """Test model command with no args shows current model."""
        from run import handle_model_command
        
        with patch('utils.api_keys.get_current_model', return_value='test-model'):
            handle_model_command([])
        
        captured = capsys.readouterr()
        assert 'Current model' in captured.out
        assert 'test-model' in captured.out
    
    def test_model_help_shows_current(self, mock_env_vars, capsys):
        """Test model -h shows current model."""
        from run import handle_model_command
        
        with patch('utils.api_keys.get_current_model', return_value='test-model'):
            handle_model_command(['-h'])
        
        captured = capsys.readouterr()
        assert 'Current model' in captured.out
    
    def test_model_list_slots_calls_function(self, mock_env_vars):
        """Test model -list-slots calls list_model_slots."""
        from run import handle_model_command
        
        with patch('utils.api_keys.list_model_slots') as mock_list:
            handle_model_command(['-list-slots'])
            mock_list.assert_called_once()


class TestHandleMultiCommand:
    """Tests for handle_multi_command function."""
    
    def test_multi_no_args_shows_help(self, mock_env_vars, capsys):
        """Test multi command with no args shows help."""
        from run import handle_multi_command
        
        handle_multi_command([])
        
        captured = capsys.readouterr()
        assert 'update-all' in captured.out
        assert 'add-list' in captured.out


class TestMain:
    """Tests for main function."""
    
    def test_main_no_args_shows_help(self, mock_env_vars, monkeypatch, capsys):
        """Test main with no args shows help."""
        from run import main
        
        monkeypatch.setattr('sys.argv', ['run.py'])
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        # Should exit with 0 (help shown, not error)
        assert exc_info.value.code == 0
        
        captured = capsys.readouterr()
        assert 'Available Commands' in captured.out
    
    def test_main_unknown_command(self, mock_env_vars, monkeypatch, capsys):
        """Test main with unknown command shows error."""
        from run import main
        
        monkeypatch.setattr('sys.argv', ['run.py', 'unknown_command'])
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
        
        captured = capsys.readouterr()
        assert 'Unknown command' in captured.out
    
    def test_main_model_command(self, mock_env_vars, monkeypatch):
        """Test main routes model command correctly."""
        from run import main
        
        monkeypatch.setattr('sys.argv', ['run.py', 'model'])
        
        with patch('run.handle_model_command') as mock_handler:
            main()
            mock_handler.assert_called_once_with([])
    
    def test_main_multi_command(self, mock_env_vars, monkeypatch):
        """Test main routes multi command correctly."""
        from run import main
        
        monkeypatch.setattr('sys.argv', ['run.py', 'multi', 'update-all'])
        
        with patch('run.handle_multi_command') as mock_handler:
            main()
            mock_handler.assert_called_once_with(['update-all'])
    
    def test_main_valid_command_calls_subprocess(self, mock_env_vars, monkeypatch):
        """Test main calls subprocess for valid command."""
        from run import main
        
        monkeypatch.setattr('sys.argv', ['run.py', 'monitor'])
        
        with patch('subprocess.run') as mock_run:
            main()
            mock_run.assert_called_once()
            # Check that it was called with the right script
            call_args = mock_run.call_args[0][0]
            assert 'python' in call_args[0]
            assert 'monitor' in call_args[1]


class TestCLIIntegration:
    """Integration tests for CLI."""
    
    def test_help_command(self):
        """Test running help command."""
        result = subprocess.run(
            ['python', 'run.py'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert 'SEC Filing Tracker' in result.stdout
    
    def test_unknown_command_error(self):
        """Test unknown command returns error."""
        result = subprocess.run(
            ['python', 'run.py', 'definitely_not_a_command'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 1
        assert 'Unknown command' in result.stdout or 'Unknown command' in result.stderr


class TestCLIEdgeCases:
    """Tests for edge cases in CLI."""
    
    def test_command_with_args_passes_args(self, mock_env_vars, monkeypatch):
        """Test that command arguments are passed through."""
        from run import main
        
        monkeypatch.setattr('sys.argv', ['run.py', 'scan', 'AAPL'])
        
        with patch('subprocess.run') as mock_run:
            main()
            call_args = mock_run.call_args[0][0]
            assert 'AAPL' in call_args
    
    def test_model_switch_with_slot(self, mock_env_vars, monkeypatch):
        """Test model switch with slot number."""
        from run import handle_model_command
        
        with patch('utils.api_keys.switch_model') as mock_switch:
            handle_model_command(['-switch', '-slot', '1'])
            mock_switch.assert_called_once_with(1)
    
    def test_model_load_slot_valid(self, mock_env_vars, monkeypatch, capsys):
        """Test loading model from valid slot."""
        from run import handle_model_command
        
        with patch('utils.api_keys.get_slot_model', return_value='test-model'):
            with patch('utils.api_keys.set_model') as mock_set:
                handle_model_command(['-load-slot', '1'])
                mock_set.assert_called_once_with('test-model')
    
    def test_model_load_slot_empty(self, mock_env_vars, monkeypatch, capsys):
        """Test loading from empty slot."""
        from run import handle_model_command
        
        with patch('utils.api_keys.get_slot_model', return_value=None):
            handle_model_command(['-load-slot', '99'])
        
        captured = capsys.readouterr()
        assert 'No model configured in slot' in captured.out
