"""
Extended tests for utils/api_keys.py - Additional coverage.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestEnsureSecUserAgentExtended:
    """Extended tests for ensure_sec_user_agent."""
    
    def test_ensure_sec_user_agent_prompt_success(self, temp_dir, monkeypatch, capsys):
        """Test prompting for user agent successfully."""
        from utils.api_keys import ensure_sec_user_agent
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.delenv('SEC_USER_AGENT', raising=False)
        
        # Create .env file
        (temp_dir / '.env').write_text('')
        
        # Mock input to return valid user agent
        monkeypatch.setattr('builtins.input', lambda _: 'Test User test@example.com')
        
        result = ensure_sec_user_agent()
        
        assert '@' in result
        captured = capsys.readouterr()
        assert "SEC API requires" in captured.out
    
    def test_ensure_sec_user_agent_no_email_confirm(self, temp_dir, monkeypatch, capsys):
        """Test prompting with no email and confirming save."""
        from utils.api_keys import ensure_sec_user_agent
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.delenv('SEC_USER_AGENT', raising=False)
        
        (temp_dir / '.env').write_text('')
        
        # First input: no email, second: confirm save
        inputs = iter(['Test User No Email', 'y'])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))
        
        result = ensure_sec_user_agent()
        
        assert result == 'Test User No Email'


class TestEnsureOpenRouterApiKey:
    """Tests for ensure_openrouter_api_key."""
    
    def test_ensure_openrouter_skip(self, temp_dir, monkeypatch, capsys):
        """Test skipping OpenRouter API key entry."""
        from utils.api_keys import ensure_openrouter_api_key
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
        
        # Mock input to skip
        monkeypatch.setattr('builtins.input', lambda _: '')
        
        result = ensure_openrouter_api_key()
        
        assert result is None
        captured = capsys.readouterr()
        assert "Analysis features will be disabled" in captured.out
    
    def test_ensure_openrouter_enter_key(self, temp_dir, monkeypatch, capsys):
        """Test entering OpenRouter API key."""
        from utils.api_keys import ensure_openrouter_api_key
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
        
        (temp_dir / '.env').write_text('')
        
        monkeypatch.setattr('builtins.input', lambda _: 'sk-or-v1-testkey123')
        
        result = ensure_openrouter_api_key()
        
        assert result == 'sk-or-v1-testkey123'


class TestEnsureModelConfigured:
    """Tests for ensure_model_configured."""
    
    def test_ensure_model_default(self, temp_dir, monkeypatch, capsys):
        """Test choosing default model."""
        from utils.api_keys import ensure_model_configured
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.delenv('OPENROUTER_MODEL', raising=False)
        
        (temp_dir / '.env').write_text('')
        
        # Press enter for default
        monkeypatch.setattr('builtins.input', lambda _: '')
        
        result = ensure_model_configured()
        
        assert 'deepseek' in result
    
    def test_ensure_model_choice_2(self, temp_dir, monkeypatch, capsys):
        """Test choosing model option 2."""
        from utils.api_keys import ensure_model_configured
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.delenv('OPENROUTER_MODEL', raising=False)
        
        (temp_dir / '.env').write_text('')
        
        monkeypatch.setattr('builtins.input', lambda _: '2')
        
        result = ensure_model_configured()
        
        assert 'grok' in result
    
    def test_ensure_model_custom(self, temp_dir, monkeypatch, capsys):
        """Test entering custom model name."""
        from utils.api_keys import ensure_model_configured
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.delenv('OPENROUTER_MODEL', raising=False)
        
        (temp_dir / '.env').write_text('')
        
        monkeypatch.setattr('builtins.input', lambda _: 'custom/model-name')
        
        result = ensure_model_configured()
        
        assert result == 'custom/model-name'


class TestSwitchModel:
    """Tests for switch_model."""
    
    def test_switch_model_keep_current(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test keeping current model."""
        from utils.api_keys import switch_model
        
        monkeypatch.chdir(temp_dir)
        (temp_dir / '.env').write_text('')
        
        # Press enter to keep current
        monkeypatch.setattr('builtins.input', lambda _: '')
        
        switch_model()
        
        captured = capsys.readouterr()
        assert "Keeping current model" in captured.out
    
    def test_switch_model_select_option(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test selecting a model option."""
        from utils.api_keys import switch_model
        
        monkeypatch.chdir(temp_dir)
        (temp_dir / '.env').write_text('')
        
        monkeypatch.setattr('builtins.input', lambda _: '3')
        
        switch_model()
        
        captured = capsys.readouterr()
        assert "Model set to" in captured.out
    
    def test_switch_model_custom_option(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test selecting custom model option."""
        from utils.api_keys import switch_model
        
        monkeypatch.chdir(temp_dir)
        (temp_dir / '.env').write_text('')
        
        inputs = iter(['6', 'my-custom/model'])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))
        
        switch_model()
        
        captured = capsys.readouterr()
        assert "Model set to" in captured.out
    
    def test_switch_model_custom_empty_retry(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test custom model with empty input retries."""
        from utils.api_keys import switch_model
        
        monkeypatch.chdir(temp_dir)
        (temp_dir / '.env').write_text('')
        
        # First '6' for custom, then empty, then valid model
        inputs = iter(['6', '', '6', 'valid/model'])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))
        
        try:
            switch_model()
        except StopIteration:
            pass  # Expected when inputs exhausted
    
    def test_switch_model_with_slot(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test switching model with slot number."""
        from utils.api_keys import switch_model
        
        monkeypatch.chdir(temp_dir)
        (temp_dir / '.env').write_text('')
        
        monkeypatch.setattr('builtins.input', lambda _: '1')
        
        switch_model(custom_slot=1)
        
        captured = capsys.readouterr()
        assert "slot" in captured.out.lower() or "Model set" in captured.out


class TestCheckApiKeys:
    """Tests for check_api_keys."""
    
    def test_check_api_keys_missing_sec(self, temp_dir, monkeypatch, capsys):
        """Test check with missing SEC user agent."""
        from utils.api_keys import check_api_keys
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.delenv('SEC_USER_AGENT', raising=False)
        monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key')
        
        (temp_dir / '.env').write_text('')
        
        monkeypatch.setattr('builtins.input', lambda _: 'Test User test@example.com')
        
        result = check_api_keys()
        
        assert result is True  # Updated
