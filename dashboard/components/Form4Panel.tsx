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
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [count, setCount] = useState('50');
  const [hidePlanned, setHidePlanned] = useState(false);
  const [loading, setLoading] = useState<string | null>(null);

  // Market-wide filters
  const [marketDays, setMarketDays] = useState('30');
  const [marketStartDate, setMarketStartDate] = useState('');
  const [marketEndDate, setMarketEndDate] = useState('');
  const [marketCount, setMarketCount] = useState('50');
  const [marketHidePlanned, setMarketHidePlanned] = useState(false);
  const [minAmount, setMinAmount] = useState('');
  const [maxAmount, setMaxAmount] = useState('');
  const [sortByActive, setSortByActive] = useState(false);

  const handleGetCompany = async () => {
    setLoading('company');
    const result = await form4.getCompany(ticker.toUpperCase(), {
      // Use dates if provided, otherwise fall back to days
      days: (!startDate && !endDate && days) ? parseInt(days) : undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      count: count ? parseInt(count) : undefined,
      hide_planned: hidePlanned,
    });
    onResponse(result);
    setLoading(null);
  };

  const handleGetMarket = async () => {
    setLoading('market');
    const result = await form4.getMarket({
      count: marketCount ? parseInt(marketCount) : undefined,
      // Use dates if provided, otherwise fall back to days
      days: (!marketStartDate && !marketEndDate && marketDays) ? parseInt(marketDays) : undefined,
      start_date: marketStartDate || undefined,
      end_date: marketEndDate || undefined,
      hide_planned: marketHidePlanned,
      min_amount: minAmount ? parseFloat(minAmount) : undefined,
      max_amount: maxAmount ? parseFloat(maxAmount) : undefined,
      active: sortByActive,
    });
    onResponse(result);
    setLoading(null);
  };

  return (
    <div className="space-y-6">
      <div className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
        <h3 className="text-sm font-medium text-zinc-300 mb-4">Company Insider Activity</h3>
        
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
            <label className="text-xs text-zinc-400">Count</label>
            <input
              type="number"
              value={count}
              onChange={(e) => setCount(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
              min="1"
            />
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Days</label>
            <input
              type="number"
              value={days}
              onChange={(e) => setDays(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
              min="1"
              max="365"
              placeholder="30"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
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
        
        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Days</label>
            <input
              type="number"
              value={marketDays}
              onChange={(e) => setMarketDays(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none text-sm"
              min="1"
              max="365"
              placeholder="30"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Start Date</label>
            <input
              type="date"
              value={marketStartDate}
              onChange={(e) => setMarketStartDate(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none text-sm"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">End Date</label>
            <input
              type="date"
              value={marketEndDate}
              onChange={(e) => setMarketEndDate(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none text-sm"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Count (1-200)</label>
            <input
              type="number"
              value={marketCount}
              onChange={(e) => setMarketCount(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none text-sm"
              min="1"
              max="200"
            />
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Min Amount ($)</label>
            <input
              type="number"
              value={minAmount}
              onChange={(e) => setMinAmount(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none text-sm"
              placeholder="e.g. 100000"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Max Amount ($)</label>
            <input
              type="number"
              value={maxAmount}
              onChange={(e) => setMaxAmount(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none text-sm"
              placeholder="e.g. 1000000"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Hide Planned</label>
            <button
              onClick={() => setMarketHidePlanned(!marketHidePlanned)}
              className={`w-full px-3 py-2 rounded-lg font-medium text-sm transition ${
                marketHidePlanned ? 'bg-emerald-600' : 'bg-zinc-700'
              }`}
            >
              {marketHidePlanned ? 'Yes' : 'No'}
            </button>
          </div>
          <div className="space-y-2">
            <label className="text-xs text-zinc-400">Sort by Activity</label>
            <button
              onClick={() => setSortByActive(!sortByActive)}
              className={`w-full px-3 py-2 rounded-lg font-medium text-sm transition ${
                sortByActive ? 'bg-emerald-600' : 'bg-zinc-700'
              }`}
            >
              {sortByActive ? 'Yes' : 'No'}
            </button>
          </div>
        </div>

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
