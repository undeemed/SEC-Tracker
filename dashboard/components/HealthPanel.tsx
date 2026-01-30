'use client';

import { useState } from 'react';
import { health } from '@/lib/api';
import { ApiResponse } from '@/lib/api';

interface HealthPanelProps {
  onResponse: (response: ApiResponse) => void;
}

export default function HealthPanel({ onResponse }: HealthPanelProps) {
  const [loading, setLoading] = useState(false);

  const handleCheck = async () => {
    setLoading(true);
    const result = await health.check();
    onResponse(result);
    setLoading(false);
  };

  return (
    <div className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
      <h3 className="text-sm font-medium text-zinc-300 mb-4">System Health</h3>
      <p className="text-xs text-zinc-400 mb-4">
        Check API, PostgreSQL, and Redis connectivity status.
      </p>
      <button
        onClick={handleCheck}
        disabled={loading}
        className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg font-medium transition"
      >
        {loading ? 'Checking...' : 'GET /api/v1/health'}
      </button>
    </div>
  );
}
