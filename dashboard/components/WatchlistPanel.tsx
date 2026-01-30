'use client';

import { useState } from 'react';
import { watchlist } from '@/lib/api';
import { ApiResponse } from '@/lib/api';

interface WatchlistPanelProps {
  onResponse: (response: ApiResponse) => void;
}

export default function WatchlistPanel({ onResponse }: WatchlistPanelProps) {
  const [ticker, setTicker] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState<string | null>(null);

  const handleGet = async () => {
    setLoading('get');
    const result = await watchlist.get();
    onResponse(result);
    setLoading(null);
  };

  const handleAdd = async () => {
    setLoading('add');
    const result = await watchlist.add(ticker.toUpperCase());
    onResponse(result);
    setLoading(null);
    if (!result.error) setTicker('');
  };

  const handleRemove = async () => {
    setLoading('remove');
    const result = await watchlist.remove(ticker.toUpperCase());
    onResponse(result);
    setLoading(null);
    if (!result.error) setTicker('');
  };

  const handleSearch = async () => {
    setLoading('search');
    const result = await watchlist.search(searchQuery);
    onResponse(result);
    setLoading(null);
  };

  return (
    <div className="space-y-6">
      <div className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
        <h3 className="text-sm font-medium text-zinc-300 mb-4">Your Watchlist</h3>
        <button
          onClick={handleGet}
          disabled={loading !== null}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg font-medium transition"
        >
          {loading === 'get' ? 'Fetching...' : 'GET /api/v1/watchlist/'}
        </button>
      </div>

      <div className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
        <h3 className="text-sm font-medium text-zinc-300 mb-4">Add / Remove Ticker</h3>
        
        <div className="space-y-2 mb-4">
          <label className="text-xs text-zinc-400">Ticker</label>
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
            placeholder="NVDA"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={handleAdd}
            disabled={loading !== null || !ticker}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg font-medium transition"
          >
            {loading === 'add' ? 'Adding...' : 'Add to Watchlist'}
          </button>
          <button
            onClick={handleRemove}
            disabled={loading !== null || !ticker}
            className="px-4 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-50 rounded-lg font-medium transition"
          >
            {loading === 'remove' ? 'Removing...' : 'Remove from Watchlist'}
          </button>
        </div>
      </div>

      <div className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
        <h3 className="text-sm font-medium text-zinc-300 mb-4">Search Companies</h3>
        
        <div className="space-y-2 mb-4">
          <label className="text-xs text-zinc-400">Search Query</label>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm"
            placeholder="apple, nvidia, microsoft..."
          />
        </div>

        <button
          onClick={handleSearch}
          disabled={loading !== null || !searchQuery}
          className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 rounded-lg font-medium transition"
        >
          {loading === 'search' ? 'Searching...' : 'GET /api/v1/watchlist/search'}
        </button>
      </div>
    </div>
  );
}
