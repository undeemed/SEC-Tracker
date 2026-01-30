'use client';

import { useState } from 'react';
import { form4 } from '@/lib/api';
import { ApiResponse } from '@/lib/api';

interface Form4PanelProps {
  onResponse: (response: ApiResponse) => void;
}

export default function Form4Panel({ onResponse }: Form4PanelProps) {
  const [ticker, setTicker] = useState('AAPL');
  const [days, setDays] = useState('30');
  const [count, setCount] = useState('50');
  const [hidePlanned, setHidePlanned] = useState(false);
  const [loading, setLoading] = useState<string | null>(null);

  const handleGetCompany = async () => {
    setLoading('company');
    const result = await form4.getCompany(ticker.toUpperCase(), {
      days: days ? parseInt(days) : undefined,
      count: count ? parseInt(count) : undefined,
      hide_planned: hidePlanned,
    });
    onResponse(result);
    setLoading(null);
  };

  const handleGetMarket = async () => {
    setLoading('market');
    const result = await form4.getMarket();
    onResponse(result);
    setLoading(null);
  };

  return (
    <div className="space-y-6">
      <div className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
        <h3 className="text-sm font-medium text-zinc-300 mb-4">Company Insider Activity</h3>
        
        <div className="grid grid-cols-4 gap-4 mb-4">
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
            <label className="text-xs text-zinc-400">Days (1-365)</label>
            <input
              type="number"
              value={days}
              onChange={(e) => setDays(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
              min="1"
              max="365"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Count</label>
            <input
              type="number"
              value={count}
              onChange={(e) => setCount(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
              min="1"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Hide Planned</label>
            <button
              onClick={() => setHidePlanned(!hidePlanned)}
              className={`w-full px-3 py-2 rounded-lg font-medium text-sm transition ${
                hidePlanned ? 'bg-blue-600' : 'bg-zinc-700'
              }`}
            >
              {hidePlanned ? 'Yes' : 'No'}
            </button>
          </div>
        </div>

        <button
          onClick={handleGetCompany}
          disabled={loading !== null || !ticker}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg font-medium transition"
        >
          {loading === 'company' ? 'Fetching...' : `GET /api/v1/form4/${ticker || '{ticker}'}`}
        </button>
      </div>

      <div className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
        <h3 className="text-sm font-medium text-zinc-300 mb-4">Market-Wide Activity</h3>
        <button
          onClick={handleGetMarket}
          disabled={loading !== null}
          className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg font-medium transition"
        >
          {loading === 'market' ? 'Fetching...' : 'GET /api/v1/form4/'}
        </button>
      </div>
    </div>
  );
}
