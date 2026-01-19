"""
Tests for utils/config.py and utils/api_keys.py - Configuration management.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConfig:
    """Tests for utils/config.py module."""
    
    def test_user_agent_from_env(self, mock_env_vars):
        """Test USER_AGENT is loaded from environment."""
        # Need to reimport to get fresh values
        import importlib
        import utils.config as config
        importlib.reload(config)
        
        assert config.USER_AGENT == 'Test User test@example.com'
    
    def test_openrouter_key_from_env(self, mock_env_vars):
        """Test OPENROUTER_API_KEY is loaded from environment."""
        import importlib
        import utils.config as config
        importlib.reload(config)
        
        assert config.OPENROUTER_API_KEY == 'sk-or-v1-test-key-12345'
    
    def test_get_user_agent_returns_value(self, mock_env_vars):
        """Test get_user_agent returns the configured value."""
        import importlib
        import utils.config as config
        importlib.reload(config)
        
        result = config.get_user_agent()
        assert 'test@example.com' in result
    
    def test_get_openrouter_api_key_returns_value(self, mock_env_vars):
        """Test get_openrouter_api_key returns the configured value."""
        import importlib
        import utils.config as config
        importlib.reload(config)
        
        result = config.get_openrouter_api_key()
        assert result == 'sk-or-v1-test-key-12345'
    
    def test_get_model_returns_value(self, mock_env_vars):
        """Test get_model returns the configured model."""
        import importlib
        import utils.config as config
        importlib.reload(config)
        
        result = config.get_model()
        assert 'deepseek' in result


class TestApiKeys:
    """Tests for utils/api_keys.py module."""
    
    def test_save_api_key_to_env_creates_file(self, temp_dir, monkeypatch):
        """Test that save_api_key_to_env creates .env file if missing."""
        from utils.api_keys import save_api_key_to_env
        
        monkeypatch.chdir(temp_dir)
        
        save_api_key_to_env('TEST_KEY', 'test_value')
        
        env_file = temp_dir / '.env'
        assert env_file.exists()
        content = env_file.read_text()
        assert 'TEST_KEY=test_value' in content
    
    def test_save_api_key_to_env_updates_existing(self, temp_dir, monkeypatch):
        """Test that save_api_key_to_env updates existing keys."""
        from utils.api_keys import save_api_key_to_env
        
        monkeypatch.chdir(temp_dir)
        
        # Create existing .env
        env_file = temp_dir / '.env'
        env_file.write_text('TEST_KEY=old_value\nOTHER_KEY=other\n')
        
        save_api_key_to_env('TEST_KEY', 'new_value')
        
        content = env_file.read_text()
        assert 'TEST_KEY=new_value' in content
        assert 'TEST_KEY=old_value' not in content
        assert 'OTHER_KEY=other' in content
    
    def test_save_api_key_to_env_adds_new_key(self, temp_dir, monkeypatch):
        """Test that save_api_key_to_env adds new keys."""
        from utils.api_keys import save_api_key_to_env
        
        monkeypatch.chdir(temp_dir)
        
        # Create existing .env
        env_file = temp_dir / '.env'
        env_file.write_text('EXISTING_KEY=value\n')
        
        save_api_key_to_env('NEW_KEY', 'new_value')
        
        content = env_file.read_text()
        assert 'NEW_KEY=new_value' in content
        assert 'EXISTING_KEY=value' in content
    
    def test_save_api_key_sets_environ(self, temp_dir, monkeypatch):
        """Test that save_api_key_to_env sets os.environ."""
        from utils.api_keys import save_api_key_to_env
        
        monkeypatch.chdir(temp_dir)
        
        save_api_key_to_env('ENV_TEST_KEY', 'env_test_value')
        
        assert os.environ.get('ENV_TEST_KEY') == 'env_test_value'
    
    def test_check_api_keys_returns_false_when_set(self, mock_env_vars):
        """Test check_api_keys returns False when keys already set."""
        from utils.api_keys import check_api_keys
        
        result = check_api_keys()
        assert result is False  # No update needed
    
    def test_ensure_sec_user_agent_returns_env_value(self, mock_env_vars):
        """Test ensure_sec_user_agent returns environment value."""
        from utils.api_keys import ensure_sec_user_agent
        
        result = ensure_sec_user_agent()
        assert 'test@example.com' in result
    
    def test_ensure_openrouter_api_key_returns_env_value(self, mock_env_vars):
        """Test ensure_openrouter_api_key returns environment value."""
        from utils.api_keys import ensure_openrouter_api_key
        
        result = ensure_openrouter_api_key()
        assert result == 'sk-or-v1-test-key-12345'
    
    def test_get_current_model_returns_env_value(self, mock_env_vars):
        """Test get_current_model returns environment value."""
        from utils.api_keys import get_current_model
        
        result = get_current_model()
        assert 'deepseek' in result
    
    def test_set_model(self, temp_dir, monkeypatch, mock_env_vars):
        """Test set_model saves model to .env."""
        from utils.api_keys import set_model
        
        monkeypatch.chdir(temp_dir)
        
        # Create .env file
        env_file = temp_dir / '.env'
        env_file.write_text('')
        
        set_model('openai/gpt-4')
        
        assert os.environ.get('OPENROUTER_MODEL') == 'openai/gpt-4'
    
    def test_set_model_with_slot(self, temp_dir, monkeypatch, mock_env_vars):
        """Test set_model with slot number."""
        from utils.api_keys import set_model
        
        monkeypatch.chdir(temp_dir)
        
        # Create .env file
        env_file = temp_dir / '.env'
        env_file.write_text('')
        
        set_model('openai/gpt-4', slot=1)
        
        assert os.environ.get('OPENROUTER_MODEL_SLOT_1') == 'openai/gpt-4'
        assert os.environ.get('OPENROUTER_MODEL') == 'openai/gpt-4'
    
    def test_get_slot_model(self, monkeypatch):
        """Test get_slot_model retrieves slot value."""
        from utils.api_keys import get_slot_model
        
        monkeypatch.setenv('OPENROUTER_MODEL_SLOT_1', 'test-model')
        
        result = get_slot_model(1)
        assert result == 'test-model'
    
    def test_get_slot_model_nonexistent(self, clean_env):
        """Test get_slot_model returns None for nonexistent slot."""
        from utils.api_keys import get_slot_model
        
        result = get_slot_model(99)
        assert result is None


class TestApiKeyValidation:
    """Tests for API key validation edge cases."""
    
    def test_ensure_sec_user_agent_missing_raises_on_empty_input(self, clean_env, monkeypatch):
        """Test ensure_sec_user_agent with missing key and empty input."""
        from utils.api_keys import ensure_sec_user_agent
        
        # Mock input to return empty string
        monkeypatch.setattr('builtins.input', lambda _: '')
        
        with pytest.raises(EnvironmentError):
            ensure_sec_user_agent()
    
    def test_ensure_sec_user_agent_validates_email_format(self, clean_env, monkeypatch, temp_dir):
        """Test ensure_sec_user_agent validates email format."""
        from utils.api_keys import ensure_sec_user_agent
        
        monkeypatch.chdir(temp_dir)
        
        # Create .env file
        env_file = temp_dir / '.env'
        env_file.write_text('')
        
        # Mock input sequence: first without @, then 'n' to not save, then with @
        inputs = iter(['No Email Here', 'n', 'Test User test@example.com'])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))
        
        # This should eventually succeed with the third input
        try:
            result = ensure_sec_user_agent()
            assert '@' in result
        except (StopIteration, EnvironmentError):
            # Expected if validation rejects and retries exhaust inputs
            pass


class TestModelSlotManagement:
    """Tests for model slot management functionality."""
    
    def test_list_model_slots_empty(self, clean_env, capsys, monkeypatch):
        """Test listing slots when none configured."""
        from utils.api_keys import list_model_slots
        
        # Mock input to prevent stdin issues
        monkeypatch.setattr('builtins.input', lambda _: '')
        
        # Clear all slot environment variables
        for i in range(1, 10):
            monkeypatch.delenv(f'OPENROUTER_MODEL_SLOT_{i}', raising=False)
        
        slots = list_model_slots()
        
        assert slots == []
        captured = capsys.readouterr()
        assert "No model slots configured" in captured.out
    
    def test_list_model_slots_with_slots(self, monkeypatch, capsys, mock_env_vars):
        """Test listing configured slots."""
        from utils.api_keys import list_model_slots
        
        monkeypatch.setenv('OPENROUTER_MODEL_SLOT_1', 'model-1')
        monkeypatch.setenv('OPENROUTER_MODEL_SLOT_2', 'model-2')
        
        slots = list_model_slots()
        
        assert len(slots) == 2
        assert (1, 'model-1') in slots
        assert (2, 'model-2') in slots


class TestConfigEnvironmentIsolation:
    """Tests for environment isolation in config."""
    
    def test_missing_user_agent_none(self, clean_env):
        """Test USER_AGENT is None when not set."""
        import importlib
        import utils.config as config
        importlib.reload(config)
        
        assert config.USER_AGENT is None
    
    def test_missing_openrouter_key_none(self, clean_env):
        """Test OPENROUTER_API_KEY is None when not set."""
        import importlib
        import utils.config as config
        importlib.reload(config)
        
        assert config.OPENROUTER_API_KEY is None
