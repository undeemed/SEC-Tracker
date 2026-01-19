"""
Tests for services/monitor.py - Filing system monitoring.
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFilingMonitor:
    """Tests for FilingMonitor class."""
    
    def test_monitor_creation(self, temp_dir, monkeypatch):
        """Test FilingMonitor can be created."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        monitor = FilingMonitor()
        assert monitor is not None
    
    def test_load_state_empty(self, temp_dir, monkeypatch):
        """Test loading state when no state file exists."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        monitor = FilingMonitor()
        state = monitor.load_state()
        
        assert state == {}
    
    def test_load_state_existing(self, temp_dir, sample_filing_state, monkeypatch):
        """Test loading existing state file."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        monitor = FilingMonitor()
        state = monitor.load_state()
        
        assert 'filings' in state
        assert len(state['filings']) > 0
    
    def test_get_filing_stats(self, temp_dir, sample_filing_state, monkeypatch):
        """Test getting filing statistics."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        monitor = FilingMonitor()
        state = monitor.load_state()
        stats = monitor.get_filing_stats(state)
        
        assert 'total_filings' in stats
        assert 'by_form' in stats
        assert 'recent_7d' in stats
        assert 'recent_30d' in stats
    
    def test_get_filing_stats_counts_forms(self, temp_dir, sample_filing_state, monkeypatch):
        """Test that filing stats counts forms correctly."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        monitor = FilingMonitor()
        state = monitor.load_state()
        stats = monitor.get_filing_stats(state)
        
        # Should count 10-K and 8-K from sample
        assert stats['by_form']['10-K'] == 1
        assert stats['by_form']['8-K'] == 1
    
    def test_get_analysis_info(self, temp_dir, sample_filing_state, monkeypatch):
        """Test getting analysis information."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        monitor = FilingMonitor()
        state = monitor.load_state()
        info = monitor.get_analysis_info(state)
        
        assert '10-K' in info
        assert 'last_analysis' in info['10-K']
        assert 'hours_ago' in info['10-K']
        assert 'needs_update' in info['10-K']
    
    def test_check_needs_update_no_analysis(self, temp_dir, monkeypatch):
        """Test needs_update when never analyzed."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps({
            'filings': {
                'test': {'form': '10-K', 'downloaded_at': datetime.now().isoformat()}
            },
            'analyzed': {}
        }))
        
        monitor = FilingMonitor()
        state = monitor.load_state()
        
        assert monitor.check_needs_update('10-K', state) is True
    
    def test_check_needs_update_newer_filing(self, temp_dir, monkeypatch):
        """Test needs_update with newer filing."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        old_analysis = (datetime.now() - timedelta(hours=2)).isoformat()
        new_download = datetime.now().isoformat()
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps({
            'filings': {
                'test': {'form': '10-K', 'downloaded_at': new_download, 'filing_date': '2025-01-15'}
            },
            'analyzed': {
                '10-K': old_analysis
            }
        }))
        
        monitor = FilingMonitor()
        state = monitor.load_state()
        
        assert monitor.check_needs_update('10-K', state) is True


class TestDiskUsage:
    """Tests for disk usage calculation."""
    
    def test_get_disk_usage_empty(self, temp_dir, monkeypatch):
        """Test disk usage with no filings."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        # Create empty filings directory
        (temp_dir / 'sec_filings').mkdir()
        
        monitor = FilingMonitor()
        usage = monitor.get_disk_usage()
        
        assert 'total' in usage
        assert usage['total'] == 0
    
    def test_get_disk_usage_with_files(self, temp_dir, monkeypatch):
        """Test disk usage with filing files."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        # Create filings directory with files
        filings_dir = temp_dir / 'sec_filings' / '10-K'
        filings_dir.mkdir(parents=True)
        
        (filings_dir / 'test1.html').write_text('x' * 1000)  # 1KB
        (filings_dir / 'test2.html').write_text('x' * 1000)  # 1KB
        
        monitor = FilingMonitor()
        usage = monitor.get_disk_usage()
        
        assert usage['total'] > 0
        assert '10-K' in usage


class TestPrintDashboard:
    """Tests for dashboard printing."""
    
    def test_print_dashboard_no_state(self, temp_dir, monkeypatch, capsys):
        """Test dashboard with no state file."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        monitor = FilingMonitor()
        monitor.print_dashboard()
        
        captured = capsys.readouterr()
        assert 'No tracking state found' in captured.out
    
    def test_print_dashboard_with_state(self, temp_dir, sample_filing_state, monkeypatch, capsys):
        """Test dashboard with state file."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        # Create directories
        (temp_dir / 'sec_filings').mkdir()
        (temp_dir / 'analysis_results').mkdir()
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        monitor = FilingMonitor()
        monitor.print_dashboard()
        
        captured = capsys.readouterr()
        assert 'SEC Filing System Monitor' in captured.out
        assert 'Filing Statistics' in captured.out


class TestExportMetrics:
    """Tests for metrics export."""
    
    def test_export_metrics(self, temp_dir, sample_filing_state, monkeypatch):
        """Test exporting metrics to JSON."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        # Create directories
        (temp_dir / 'sec_filings').mkdir()
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps(sample_filing_state))
        
        monitor = FilingMonitor()
        monitor.export_metrics('metrics_test.json')
        
        metrics_file = temp_dir / 'metrics_test.json'
        assert metrics_file.exists()
        
        metrics = json.loads(metrics_file.read_text())
        assert 'timestamp' in metrics
        assert 'filings' in metrics
        assert 'analysis' in metrics


class TestCheckAlerts:
    """Tests for alert checking."""
    
    def test_check_alerts_stale_check(self, temp_dir, monkeypatch):
        """Test alert for stale last check."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        # Create sec_filings directory to avoid FileNotFoundError
        (temp_dir / 'sec_filings').mkdir()
        
        old_check = (datetime.now() - timedelta(hours=50)).isoformat()
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps({
            'last_check': old_check,
            'filings': {},
            'analyzed': {}
        }))
        
        monitor = FilingMonitor()
        alerts = monitor.check_alerts()
        
        assert len(alerts) > 0
        assert any('CRITICAL' in alert for alert in alerts)
    
    def test_check_alerts_stale_analysis(self, temp_dir, monkeypatch):
        """Test alert for stale analysis."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        # Create sec_filings directory to avoid FileNotFoundError
        (temp_dir / 'sec_filings').mkdir()
        
        old_analysis = (datetime.now() - timedelta(days=10)).isoformat()
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps({
            'last_check': datetime.now().isoformat(),
            'filings': {
                'test': {'form': '10-K', 'downloaded_at': datetime.now().isoformat(), 'filing_date': '2025-01-15'}
            },
            'analyzed': {
                '10-K': old_analysis
            }
        }))
        
        monitor = FilingMonitor()
        alerts = monitor.check_alerts()
        
        assert len(alerts) > 0
        assert any('WARNING' in alert and '10-K' in alert for alert in alerts)
    
    def test_check_alerts_no_issues(self, temp_dir, monkeypatch):
        """Test no alerts when everything is up to date."""
        from services.monitor import FilingMonitor
        
        monkeypatch.chdir(temp_dir)
        
        (temp_dir / 'sec_filings').mkdir()
        
        recent_time = datetime.now().isoformat()
        
        state_file = temp_dir / 'filing_state.json'
        state_file.write_text(json.dumps({
            'last_check': recent_time,
            'filings': {},
            'analyzed': {
                '10-K': recent_time,
                '8-K': recent_time
            }
        }))
        
        monitor = FilingMonitor()
        alerts = monitor.check_alerts()
        
        # Might have some minor alerts but no critical ones
        critical_alerts = [a for a in alerts if 'CRITICAL' in a]
        assert len(critical_alerts) == 0
