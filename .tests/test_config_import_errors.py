"""
Tests for config.py ImportError handling paths.
These tests cover the except ImportError branches by patching imports.
"""

import pytest
import os
import sys
import builtins
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib

sys.path.insert(0, str(Path(__file__).parent.parent))


def make_import_raiser(blocked_modules):
    """Create a function that raises ImportError for specific modules."""
    original_import = builtins.__import__
    
    def custom_import(name, globals=None, locals=None, fromlist=(), level=0):
        if any(blocked in name for blocked in blocked_modules):
            raise ImportError(f"Blocked: {name}")
        return original_import(name, globals, locals, fromlist, level)
    
    return custom_import


class TestGetUserAgentImportErrorReal:
    """Tests for get_user_agent ImportError handling - actually covers lines 32-38."""
    
    def test_import_error_fallback_with_user_agent(self, temp_dir, monkeypatch):
        """Test ImportError returns USER_AGENT when set (lines 32, 38)."""
        monkeypatch.chdir(temp_dir)
        monkeypatch.setenv('SEC_USER_AGENT', 'Fallback Test test@test.com')
        
        # First ensure config is loaded fresh
        if 'utils.config' in sys.modules:
            del sys.modules['utils.config']
        if 'utils.api_keys' in sys.modules:
            del sys.modules['utils.api_keys']
        
        # Import fresh
        import utils.config
        importlib.reload(utils.config)
        
        # Now patch __import__ for the function call
        original_import = builtins.__import__
        
        def blocking_import(name, *args, **kwargs):
            if 'api_keys' in name:
                raise ImportError(f"Test block: {name}")
            return original_import(name, *args, **kwargs)
        
        # Patch and call get_user_agent
        with patch.object(builtins, '__import__', blocking_import):
            result = utils.config.get_user_agent()
        
        assert result == 'Fallback Test test@test.com'
    
    def test_import_error_raises_without_user_agent(self, temp_dir, monkeypatch):
        """Test ImportError raises EnvironmentError when USER_AGENT not set (lines 33-37)."""
        monkeypatch.chdir(temp_dir)
        monkeypatch.delenv('SEC_USER_AGENT', raising=False)
        
        # Fresh import
        if 'utils.config' in sys.modules:
            del sys.modules['utils.config']
        if 'utils.api_keys' in sys.modules:
            del sys.modules['utils.api_keys']
        
        import utils.config
        importlib.reload(utils.config)
        
        original_import = builtins.__import__
        
        def blocking_import(name, *args, **kwargs):
            if 'api_keys' in name:
                raise ImportError(f"Test block: {name}")
            return original_import(name, *args, **kwargs)
        
        with patch.object(builtins, '__import__', blocking_import):
            with pytest.raises(EnvironmentError) as exc_info:
                utils.config.get_user_agent()
        
        assert 'SEC_USER_AGENT' in str(exc_info.value)


class TestGetOpenRouterApiKeyImportErrorReal:
    """Tests for get_openrouter_api_key ImportError handling - covers lines 50-51."""
    
    def test_import_error_returns_api_key(self, temp_dir, monkeypatch):
        """Test ImportError returns OPENROUTER_API_KEY (lines 50-51)."""
        monkeypatch.chdir(temp_dir)
        monkeypatch.setenv('OPENROUTER_API_KEY', 'fallback-key-123')
        
        if 'utils.config' in sys.modules:
            del sys.modules['utils.config']
        if 'utils.api_keys' in sys.modules:
            del sys.modules['utils.api_keys']
        
        import utils.config
        importlib.reload(utils.config)
        
        original_import = builtins.__import__
        
        def blocking_import(name, *args, **kwargs):
            if 'api_keys' in name:
                raise ImportError(f"Test block: {name}")
            return original_import(name, *args, **kwargs)
        
        with patch.object(builtins, '__import__', blocking_import):
            result = utils.config.get_openrouter_api_key()
        
        assert result == 'fallback-key-123'


class TestGetModelImportErrorReal:
    """Tests for get_model ImportError handling - covers lines 60-64."""
    
    def test_import_error_with_model_set(self, temp_dir, monkeypatch):
        """Test ImportError returns model from env (lines 60-61, 64)."""
        monkeypatch.chdir(temp_dir)
        monkeypatch.setenv('OPENROUTER_MODEL', 'fallback/model')
        
        if 'utils.config' in sys.modules:
            del sys.modules['utils.config']
        if 'utils.api_keys' in sys.modules:
            del sys.modules['utils.api_keys']
        
        import utils.config
        importlib.reload(utils.config)
        
        original_import = builtins.__import__
        
        def blocking_import(name, *args, **kwargs):
            if 'api_keys' in name:
                raise ImportError(f"Test block: {name}")
            return original_import(name, *args, **kwargs)
        
        with patch.object(builtins, '__import__', blocking_import):
            result = utils.config.get_model()
        
        assert result == 'fallback/model'
    
    def test_import_error_no_model_prints_warning(self, temp_dir, monkeypatch, capsys):
        """Test ImportError prints warning when model not set (lines 62-63)."""
        monkeypatch.chdir(temp_dir)
        monkeypatch.delenv('OPENROUTER_MODEL', raising=False)
        
        if 'utils.config' in sys.modules:
            del sys.modules['utils.config']
        if 'utils.api_keys' in sys.modules:
            del sys.modules['utils.api_keys']
        
        import utils.config
        importlib.reload(utils.config)
        
        original_import = builtins.__import__
        
        def blocking_import(name, *args, **kwargs):
            if 'api_keys' in name:
                raise ImportError(f"Test block: {name}")
            return original_import(name, *args, **kwargs)
        
        with patch.object(builtins, '__import__', blocking_import):
            result = utils.config.get_model()
        
        assert result is None
        captured = capsys.readouterr()
        assert 'Warning' in captured.out
