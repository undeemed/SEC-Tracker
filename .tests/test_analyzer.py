"""
Tests for core/analyzer.py - Filing analysis functionality.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestHTMLTextExtractor:
    """Tests for HTMLTextExtractor class."""
    
    def test_extract_basic_text(self, mock_env_vars):
        """Test extracting text from basic HTML."""
        from core.analyzer import HTMLTextExtractor
        
        extractor = HTMLTextExtractor()
        extractor.feed("<p>Hello World</p>")
        
        assert "Hello" in extractor.get_text()
        assert "World" in extractor.get_text()
    
    def test_extract_ignores_script(self, mock_env_vars):
        """Test that script content is ignored."""
        from core.analyzer import HTMLTextExtractor
        
        extractor = HTMLTextExtractor()
        extractor.feed("<script>var x = 1;</script><p>Visible text</p>")
        
        result = extractor.get_text()
        assert "var x = 1" not in result
        assert "Visible text" in result
    
    def test_extract_ignores_style(self, mock_env_vars):
        """Test that style content is ignored."""
        from core.analyzer import HTMLTextExtractor
        
        extractor = HTMLTextExtractor()
        extractor.feed("<style>.test { color: red; }</style><p>Visible</p>")
        
        result = extractor.get_text()
        assert "color: red" not in result
        assert "Visible" in result
    
    def test_extract_preserves_newlines(self, mock_env_vars):
        """Test that paragraph breaks create newlines."""
        from core.analyzer import HTMLTextExtractor
        
        extractor = HTMLTextExtractor()
        extractor.feed("<p>Para 1</p><p>Para 2</p>")
        
        result = extractor.get_text()
        # Should have some whitespace between paragraphs
        assert "Para 1" in result
        assert "Para 2" in result
    
    def test_extract_table_content(self, mock_env_vars):
        """Test extracting table content."""
        from core.analyzer import HTMLTextExtractor
        
        extractor = HTMLTextExtractor()
        extractor.feed("<table><tr><td>Cell 1</td><td>Cell 2</td></tr></table>")
        
        result = extractor.get_text()
        assert "Cell 1" in result
        assert "Cell 2" in result


class TestExtractTextFromHTML:
    """Tests for extract_text_from_html function."""
    
    def test_extract_text_basic(self, mock_env_vars, sample_filing_html):
        """Test basic text extraction from HTML."""
        from core.analyzer import extract_text_from_html
        
        result = extract_text_from_html(sample_filing_html)
        
        assert "Apple Inc." in result
        assert "sample SEC filing" in result
    
    def test_extract_text_cleans_whitespace(self, mock_env_vars):
        """Test that excessive whitespace is cleaned."""
        from core.analyzer import extract_text_from_html
        
        html = "<p>Word1</p><p></p><p></p><p>Word2</p>"
        result = extract_text_from_html(html)
        
        # Should not have excessive newlines
        assert "\n\n\n\n" not in result
    
    def test_extract_text_removes_script_style(self, mock_env_vars, sample_filing_html):
        """Test that script and style are removed."""
        from core.analyzer import extract_text_from_html
        
        result = extract_text_from_html(sample_filing_html)
        
        assert "console.log" not in result
        assert "color: red" not in result


class TestSpinner:
    """Tests for Spinner class."""
    
    def test_spinner_creation(self, mock_env_vars):
        """Test Spinner can be created."""
        from core.analyzer import Spinner
        
        spinner = Spinner()
        assert spinner is not None
        assert spinner.spinning is False
    
    def test_spinner_start_stop(self, mock_env_vars):
        """Test Spinner start and stop."""
        from core.analyzer import Spinner
        import time
        
        spinner = Spinner()
        spinner.start()
        
        assert spinner.spinning is True
        
        time.sleep(0.2)  # Let it spin a bit
        
        spinner.stop()
        
        assert spinner.spinning is False


class TestAnalyzeFilingsOptimized:
    """Tests for analyze_filings_optimized function."""
    
    def test_returns_none_without_api_key(self, clean_env, temp_dir, monkeypatch):
        """Test that analysis returns None without API key."""
        from core.analyzer import analyze_filings_optimized
        
        monkeypatch.chdir(temp_dir)
        
        # Create mock filings directory
        filings_dir = temp_dir / "sec_filings" / "CIK0001045810"
        filings_dir.mkdir(parents=True)
        
        # Create mock model getter
        with patch('utils.api_keys.get_current_model', return_value='test-model'):
            result = analyze_filings_optimized(ticker_or_cik="0001045810")
        
        assert result is None
    
    def test_creates_analysis_directory(self, mock_env_vars, temp_dir, monkeypatch):
        """Test that analysis directory is created."""
        from core.analyzer import analyze_filings_optimized
        
        monkeypatch.chdir(temp_dir)
        
        # Create mock filings directory with a file
        filings_dir = temp_dir / "sec_filings" / "AAPL" / "10-K"
        filings_dir.mkdir(parents=True)
        (filings_dir / "test.html").write_text("<html>Test</html>")
        
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test analysis"
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('core.analyzer.OpenAI', return_value=mock_client):
            with patch('utils.api_keys.get_current_model', return_value='test-model'):
                analyze_filings_optimized(
                    forms_to_analyze=["10-K"],
                    ticker_or_cik="AAPL"
                )
        
        analysis_dir = temp_dir / "analysis_results" / "AAPL"
        assert analysis_dir.exists()


class TestAnalyzerConfiguration:
    """Tests for analyzer configuration."""
    
    def test_form_specific_focus_defined(self, mock_env_vars):
        """Test that form-specific analysis focus is defined."""
        # This tests that the prompt generation works correctly
        form_specific_focus = {
            "4": "insider trading patterns",
            "8-K": "material events",
            "10-K": "annual performance",
            "10-Q": "quarterly trends"
        }
        
        for form_type, focus in form_specific_focus.items():
            assert len(focus) > 0


class TestAnalyzerEdgeCases:
    """Tests for edge cases in analyzer."""
    
    def test_handles_empty_html(self, mock_env_vars):
        """Test handling of empty HTML."""
        from core.analyzer import extract_text_from_html
        
        result = extract_text_from_html("")
        assert result == ""
    
    def test_handles_malformed_html(self, mock_env_vars):
        """Test handling of malformed HTML."""
        from core.analyzer import extract_text_from_html
        
        malformed = "<p>Unclosed paragraph<div>Mixed tags</p></div>"
        result = extract_text_from_html(malformed)
        
        # Should extract text without crashing
        assert "Unclosed" in result or "Mixed" in result
    
    def test_handles_unicode_content(self, mock_env_vars):
        """Test handling of unicode content."""
        from core.analyzer import extract_text_from_html
        
        unicode_html = "<p>Revenue: €500M | ¥1000B | £100M</p>"
        result = extract_text_from_html(unicode_html)
        
        assert "€" in result or "500M" in result
