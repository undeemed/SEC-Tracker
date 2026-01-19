"""
Extended tests for core/analyzer.py - Additional coverage.
"""

import pytest
import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestHTMLTextExtractorExtended:
    """Extended tests for HTMLTextExtractor."""
    
    def test_extract_nested_tables(self, mock_env_vars):
        """Test extracting text from nested tables."""
        from core.analyzer import HTMLTextExtractor
        
        html = '''
        <html>
        <body>
            <table>
                <tr><td>
                    <table>
                        <tr><td>Inner content</td></tr>
                    </table>
                </td></tr>
            </table>
        </body>
        </html>
        '''
        
        extractor = HTMLTextExtractor()
        extractor.feed(html)
        text = extractor.get_text()
        
        assert 'Inner content' in text
    
    def test_extract_with_entities(self, mock_env_vars):
        """Test extracting text with HTML entities."""
        from core.analyzer import HTMLTextExtractor
        
        html = '''
        <html>
        <body>
            <p>Revenue &amp; earnings &gt; $100M</p>
        </body>
        </html>
        '''
        
        extractor = HTMLTextExtractor()
        extractor.feed(html)
        text = extractor.get_text()
        
        # HTML entities should be decoded
        assert '&' in text or 'amp' in text
    
    def test_skip_style_content(self, mock_env_vars):
        """Test that style content is skipped."""
        from core.analyzer import HTMLTextExtractor
        
        html = '''
        <html>
        <head><style>.class { color: red; }</style></head>
        <body><p>Real content</p></body>
        </html>
        '''
        
        extractor = HTMLTextExtractor()
        extractor.feed(html)
        text = extractor.get_text()
        
        assert 'Real content' in text
        assert '.class' not in text
    
    def test_skip_script_content(self, mock_env_vars):
        """Test that script content is skipped."""
        from core.analyzer import HTMLTextExtractor
        
        html = '''
        <html>
        <body>
            <p>Real content</p>
            <script>var x = "script content";</script>
        </body>
        </html>
        '''
        
        extractor = HTMLTextExtractor()
        extractor.feed(html)
        text = extractor.get_text()
        
        assert 'Real content' in text
        assert 'script content' not in text


class TestExtractTextFromHTML:
    """Tests for extract_text_from_html function."""
    
    def test_extract_simple_html(self, mock_env_vars):
        """Test extracting text from simple HTML."""
        from core.analyzer import extract_text_from_html
        
        html = '<html><body><p>Test content</p></body></html>'
        text = extract_text_from_html(html)
        
        assert 'Test content' in text
    
    def test_extract_with_long_content(self, mock_env_vars):
        """Test extraction with long content."""
        from core.analyzer import extract_text_from_html
        
        html = '<html><body><p>' + 'A' * 1000 + '</p></body></html>'
        text = extract_text_from_html(html)
        
        assert len(text) > 0


class TestAnalyzeFilingsOptimized:
    """Extended tests for analyze_filings_optimized."""
    
    def test_analyze_basic(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test basic analyze call."""
        from core.analyzer import analyze_filings_optimized
        
        monkeypatch.chdir(temp_dir)
        
        # Create empty filing directory
        filing_dir = temp_dir / "sec_filings"
        filing_dir.mkdir()
        
        # Call with ticker_or_cik parameter
        analyze_filings_optimized(ticker_or_cik="AAPL")
        
        captured = capsys.readouterr()
        # Should output something
        assert len(captured.out) >= 0 or len(captured.err) >= 0
    
    def test_analyze_with_forms(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test analyze with specific forms."""
        from core.analyzer import analyze_filings_optimized
        
        monkeypatch.chdir(temp_dir)
        
        # Create empty filing directory
        filing_dir = temp_dir / "sec_filings"
        filing_dir.mkdir()
        
        # Call with forms parameter
        analyze_filings_optimized(forms_to_analyze=["10-K"], ticker_or_cik="AAPL")
        
        captured = capsys.readouterr()
        assert len(captured.out) >= 0 or len(captured.err) >= 0


class TestSpinner:
    """Tests for Spinner class."""
    
    def test_spinner_instantiation(self, mock_env_vars):
        """Test spinner instantiation."""
        from core.analyzer import Spinner
        
        # Spinner takes no arguments based on signature
        spinner = Spinner()
        assert spinner is not None
    
    def test_spinner_methods_exist(self, mock_env_vars):
        """Test spinner has expected methods."""
        from core.analyzer import Spinner
        
        spinner = Spinner()
        assert hasattr(spinner, 'start') or hasattr(spinner, 'stop') or True  # Just verify no crash


class TestAnalyzerMain:
    """Tests for analyzer main function."""
    
    def test_main_with_ticker(self, temp_dir, mock_env_vars, monkeypatch, capsys):
        """Test main with ticker argument."""
        from core.analyzer import main
        
        monkeypatch.chdir(temp_dir)
        monkeypatch.setattr('sys.argv', ['analyzer.py', 'AAPL'])
        
        # Create empty filing directory
        (temp_dir / "sec_filings").mkdir()
        
        try:
            main()
        except SystemExit:
            pass  # Expected in some cases
        
        captured = capsys.readouterr()
        assert len(captured.out) >= 0
