#!/usr/bin/env python3
"""
SEC Filing Monitor Dashboard
Provides a quick overview of the filing tracking system status
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import argparse
from typing import Dict, List

class FilingMonitor:
    """Monitor and report on SEC filing system status"""
    
    def __init__(self, state_file="filing_state.json", filings_dir="sec_filings"):
        self.state_file = Path(state_file)
        self.filings_dir = Path(filings_dir)
        self.analysis_dir = Path("analysis_results")
        
    def load_state(self) -> Dict:
        """Load the current tracking state"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {}
    
    def get_disk_usage(self) -> Dict[str, float]:
        """Calculate disk usage by form type"""
        usage = {}
        total_size = 0
        
        for form_dir in self.filings_dir.iterdir():
            if form_dir.is_dir():
                form_size = sum(f.stat().st_size for f in form_dir.glob("*.html"))
                usage[form_dir.name] = form_size / (1024 * 1024)  # MB
                total_size += form_size
        
        usage["total"] = total_size / (1024 * 1024)  # MB
        return usage
    
    def get_filing_stats(self, state: Dict) -> Dict:
        """Get statistics about filings"""
        stats = {
            "total_filings": len(state.get("filings", {})),
            "by_form": defaultdict(int),
            "recent_7d": 0,
            "recent_30d": 0,
            "oldest_filing": None,
            "newest_filing": None
        }
        
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        
        filing_dates = []
        
        for filing in state.get("filings", {}).values():
            form = filing["form"]
            stats["by_form"][form] += 1
            
            filing_date = datetime.strptime(filing["filing_date"], "%Y-%m-%d")
            filing_dates.append(filing_date)
            
            if filing_date >= seven_days_ago:
                stats["recent_7d"] += 1
            if filing_date >= thirty_days_ago:
                stats["recent_30d"] += 1
        
        if filing_dates:
            stats["oldest_filing"] = min(filing_dates)
            stats["newest_filing"] = max(filing_dates)
        
        return stats
    
    def get_analysis_info(self, state: Dict) -> Dict:
        """Get information about analyses"""
        info = {}
        
        for form, timestamp in state.get("analyzed", {}).items():
            analysis_time = datetime.fromisoformat(timestamp)
            hours_ago = (datetime.now() - analysis_time).total_seconds() / 3600
            
            info[form] = {
                "last_analysis": analysis_time,
                "hours_ago": hours_ago,
                "needs_update": self.check_needs_update(form, state)
            }
        
        return info
    
    def check_needs_update(self, form: str, state: Dict) -> bool:
        """Check if a form needs analysis update"""
        last_analysis = state.get("analyzed", {}).get(form)
        if not last_analysis:
            return True
        
        last_analysis_time = datetime.fromisoformat(last_analysis)
        
        # Check for newer filings
        for filing in state.get("filings", {}).values():
            if filing["form"] == form:
                download_time = datetime.fromisoformat(filing["downloaded_at"])
                if download_time > last_analysis_time:
                    return True
        
        return False
    
    def print_dashboard(self, verbose: bool = False):
        """Print the monitoring dashboard"""
        state = self.load_state()
        
        if not state:
            print("❌ No tracking state found. Run the tracker first.")
            return
        
        print("SEC Filing System Monitor")
        print("=" * 60)
        
        # Last check
        last_check = state.get("last_check")
        if last_check:
            check_time = datetime.fromisoformat(last_check)
            hours_ago = (datetime.now() - check_time).total_seconds() / 3600
            print(f"\n📅 Last Check: {check_time.strftime('%Y-%m-%d %H:%M:%S')} ({hours_ago:.1f} hours ago)")
        
        # Filing statistics
        stats = self.get_filing_stats(state)
        print(f"\n📊 Filing Statistics:")
        print(f"   Total tracked: {stats['total_filings']}")
        print(f"   Last 7 days:   {stats['recent_7d']}")
        print(f"   Last 30 days:  {stats['recent_30d']}")
        
        if stats['oldest_filing'] and stats['newest_filing']:
            print(f"   Date range:    {stats['oldest_filing'].strftime('%Y-%m-%d')} to {stats['newest_filing'].strftime('%Y-%m-%d')}")
        
        # By form type
        print(f"\n📋 Filings by Type:")
        for form in ["10-K", "10-Q", "8-K", "4"]:
            count = stats['by_form'].get(form, 0)
            print(f"   {form:5} {count:4d} filings")
        
        # Analysis status
        analysis_info = self.get_analysis_info(state)
        print(f"\n🔍 Analysis Status:")
        
        for form in ["10-K", "10-Q", "8-K", "4"]:
            if form in analysis_info:
                info = analysis_info[form]
                status = "🔄 NEEDS UPDATE" if info['needs_update'] else "✅ Up to date"
                print(f"   {form:5} {status} (last: {info['hours_ago']:.1f}h ago)")
            else:
                print(f"   {form:5} ❓ Never analyzed")
        
        # Disk usage
        usage = self.get_disk_usage()
        print(f"\n💾 Disk Usage:")
        print(f"   Total: {usage.get('total', 0):.1f} MB")
        
        if verbose:
            for form in ["10-K", "10-Q", "8-K", "4"]:
                if form in usage:
                    print(f"   {form:5} {usage[form]:6.1f} MB")
        
        # Recent analyses
        if self.analysis_dir.exists():
            recent_analyses = sorted(
                self.analysis_dir.glob("*.txt"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:5]
            
            if recent_analyses:
                print(f"\n📄 Recent Analyses:")
                for analysis in recent_analyses:
                    mod_time = datetime.fromtimestamp(analysis.stat().st_mtime)
                    print(f"   {analysis.name} ({mod_time.strftime('%Y-%m-%d %H:%M')})")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        recommendations = []
        
        # Check if update needed
        if hours_ago > 24:
            recommendations.append("- Run update check (last check >24h ago)")
        
        # Check for forms needing analysis
        forms_needing_update = [
            form for form, info in analysis_info.items() 
            if info.get('needs_update', False)
        ]
        if forms_needing_update:
            recommendations.append(f"- Analyze forms: {', '.join(forms_needing_update)}")
        
        # Check disk usage
        if usage.get('total', 0) > 1000:  # 1GB
            recommendations.append("- Consider archiving old filings (>1GB used)")
        
        if recommendations:
            for rec in recommendations:
                print(rec)
        else:
            print("   ✅ System is up to date!")
        
        print("\n" + "=" * 60)
    
    def export_metrics(self, output_file: str = "metrics.json"):
        """Export metrics for external monitoring"""
        state = self.load_state()
        stats = self.get_filing_stats(state)
        analysis_info = self.get_analysis_info(state)
        usage = self.get_disk_usage()
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "last_check": state.get("last_check"),
            "filings": {
                "total": stats["total_filings"],
                "recent_7d": stats["recent_7d"],
                "recent_30d": stats["recent_30d"],
                "by_form": dict(stats["by_form"])
            },
            "analysis": {
                form: {
                    "last_analysis": info["last_analysis"].isoformat(),
                    "hours_since": info["hours_ago"],
                    "needs_update": info["needs_update"]
                }
                for form, info in analysis_info.items()
            },
            "disk_usage_mb": usage
        }
        
        with open(output_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"✅ Metrics exported to {output_file}")
    
    def check_alerts(self) -> List[str]:
        """Check for conditions that should trigger alerts"""
        alerts = []
        state = self.load_state()
        
        # Check last update time
        last_check = state.get("last_check")
        if last_check:
            check_time = datetime.fromisoformat(last_check)
            hours_ago = (datetime.now() - check_time).total_seconds() / 3600
            
            if hours_ago > 48:
                alerts.append(f"CRITICAL: No update check in {hours_ago:.0f} hours")
            elif hours_ago > 24:
                alerts.append(f"WARNING: No update check in {hours_ago:.0f} hours")
        
        # Check for stale analyses
        analysis_info = self.get_analysis_info(state)
        for form, info in analysis_info.items():
            if info["hours_ago"] > 168:  # 7 days
                alerts.append(f"WARNING: {form} analysis is {info['hours_ago']:.0f} hours old")
        
        # Check disk usage
        usage = self.get_disk_usage()
        if usage.get("total", 0) > 2000:  # 2GB
            alerts.append(f"WARNING: High disk usage: {usage['total']:.0f} MB")
        
        return alerts


def main():
    parser = argparse.ArgumentParser(description='Monitor SEC Filing System')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed information')
    parser.add_argument('--export', type=str,
                       help='Export metrics to JSON file')
    parser.add_argument('--alerts', action='store_true',
                       help='Check for alert conditions')
    parser.add_argument('--json', action='store_true',
                       help='Output in JSON format')
    
    args = parser.parse_args()
    
    monitor = FilingMonitor()
    
    if args.alerts:
        alerts = monitor.check_alerts()
        if alerts:
            print("🚨 ALERTS:")
            for alert in alerts:
                print(f"   {alert}")
        else:
            print("✅ No alerts")
    elif args.export:
        monitor.export_metrics(args.export)
    elif args.json:
        # Output dashboard data as JSON
        state = monitor.load_state()
        stats = monitor.get_filing_stats(state)
        
        output = {
            "last_check": state.get("last_check"),
            "total_filings": stats["total_filings"],
            "recent_7d": stats["recent_7d"],
            "forms": dict(stats["by_form"]),
            "disk_usage_mb": monitor.get_disk_usage().get("total", 0)
        }
        print(json.dumps(output, indent=2))
    else:
        monitor.print_dashboard(verbose=args.verbose)


if __name__ == "__main__":
    main()