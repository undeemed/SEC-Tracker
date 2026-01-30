'use client';

import { useState } from 'react';
import { tracking } from '@/lib/api';
import { ApiResponse } from '@/lib/api';

interface TrackingPanelProps {
  onResponse: (response: ApiResponse) => void;
}

export default function TrackingPanel({ onResponse }: TrackingPanelProps) {
  const [ticker, setTicker] = useState('AAPL');
  const [forms, setForms] = useState('10-K,8-K');
  const [jobId, setJobId] = useState('');
  const [historyTicker, setHistoryTicker] = useState('');
  const [limit, setLimit] = useState('50');
  const [loading, setLoading] = useState<string | null>(null);

  const handleStartTracking = async () => {
    setLoading('start');
    const formList = forms.split(',').map((f) => f.trim()).filter(Boolean);
    const result = await tracking.start(ticker.toUpperCase(), formList);
    if (result.data && typeof result.data === 'object' && 'job_id' in result.data) {
      setJobId((result.data as { job_id: string }).job_id);
    }
    onResponse(result);
    setLoading(null);
  };

  const handleGetJob = async () => {
    setLoading('job');
    const result = await tracking.getJob(jobId);
    onResponse(result);
    setLoading(null);
  };

  const handleGetHistory = async () => {
    setLoading('history');
    const result = await tracking.getHistory({
      limit: limit ? parseInt(limit) : undefined,
      ticker: historyTicker || undefined,
    });
    onResponse(result);
    setLoading(null);
  };

  return (
    <div className="space-y-6">
      <div className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
        <h3 className="text-sm font-medium text-zinc-300 mb-4">Start Tracking Job</h3>
        
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Ticker</label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
              placeholder="AAPL"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Forms (comma-separated)</label>
            <input
              type="text"
              value={forms}
              onChange={(e) => setForms(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
              placeholder="10-K,8-K,10-Q"
            />
          </div>
        </div>

        <button
          onClick={handleStartTracking}
          disabled={loading !== null || !ticker}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg font-medium transition"
        >
          {loading === 'start' ? 'Starting...' : 'POST /api/v1/track/'}
        </button>
      </div>

      <div className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
        <h3 className="text-sm font-medium text-zinc-300 mb-4">Check Job Status</h3>
        
        <div className="space-y-2 mb-4">
          <label className="text-xs text-zinc-400">Job ID</label>
          <input
            type="text"
            value={jobId}
            onChange={(e) => setJobId(e.target.value)}
            className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm font-mono"
            placeholder="abc123..."
          />
        </div>

        <button
          onClick={handleGetJob}
          disabled={loading !== null || !jobId}
          className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 rounded-lg font-medium transition"
        >
          {loading === 'job' ? 'Checking...' : `GET /api/v1/track/job/${jobId || '{job_id}'}`}
        </button>
      </div>

      <div className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
        <h3 className="text-sm font-medium text-zinc-300 mb-4">Filing History</h3>
        
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Ticker (optional)</label>
            <input
              type="text"
              value={historyTicker}
              onChange={(e) => setHistoryTicker(e.target.value.toUpperCase())}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
              placeholder="Filter by ticker"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Limit</label>
            <input
              type="number"
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
              min="1"
            />
          </div>
        </div>

        <button
          onClick={handleGetHistory}
          disabled={loading !== null}
          className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg font-medium transition"
        >
          {loading === 'history' ? 'Fetching...' : 'GET /api/v1/track/history'}
        </button>
      </div>
    </div>
  );
}
