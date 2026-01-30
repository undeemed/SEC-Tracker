"""
Tests for TrackingService._run_tracking

This validates that we correctly derive "new" filings from the underlying
core tracker, which returns only a boolean from download_new_filings().
"""

from __future__ import annotations

from services.tracking_service import TrackingService


class FakeFilingTracker:
    def __init__(self):
        self.state = {
            "filings": {
                "old-acc": {
                    "form": "10-K",
                    "filing_date": "2025-01-01",
                    "downloaded_at": "2025-01-02T00:00:00",
                    "doc_url": "https://example.com/old",
                }
            }
        }


def test_run_tracking_derives_new_accessions(monkeypatch):
    import core.tracker as tracker_module

    tracker = FakeFilingTracker()

    def fake_download_new_filings(t, ticker_or_cik):
        t.state["filings"]["new-acc"] = {
            "form": "8-K",
            "filing_date": "2025-02-01",
            "downloaded_at": "2025-02-02T00:00:00",
            "doc_url": "https://example.com/new",
        }
        return True

    monkeypatch.setattr(tracker_module, "FilingTracker", lambda: tracker)
    monkeypatch.setattr(tracker_module, "download_new_filings", fake_download_new_filings)

    result = TrackingService()._run_tracking("AAPL", forms=None, analyze=False)

    assert result["filings_count"] == 1
    assert result["filings"][0]["accession"] == "new-acc"
    assert result["filings"][0]["form_type"] == "8-K"


def test_run_tracking_respects_forms_filter(monkeypatch):
    import core.tracker as tracker_module

    tracker = FakeFilingTracker()

    def fake_download_new_filings(t, ticker_or_cik):
        t.state["filings"]["new-acc"] = {
            "form": "8-K",
            "filing_date": "2025-02-01",
            "downloaded_at": "2025-02-02T00:00:00",
            "doc_url": "https://example.com/new",
        }
        return True

    monkeypatch.setattr(tracker_module, "FilingTracker", lambda: tracker)
    monkeypatch.setattr(tracker_module, "download_new_filings", fake_download_new_filings)

    result = TrackingService()._run_tracking("AAPL", forms=["10-K"], analyze=False)

    assert result["filings_count"] == 0
    assert result["filings"] == []

