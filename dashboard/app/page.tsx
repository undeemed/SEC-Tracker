'use client';

import { useState } from 'react';
import AuthPanel from '@/components/AuthPanel';
import Form4Panel from '@/components/Form4Panel';
import TrackingPanel from '@/components/TrackingPanel';
import WatchlistPanel from '@/components/WatchlistPanel';
import HealthPanel from '@/components/HealthPanel';
import ResponseViewer from '@/components/ResponseViewer';
import { ApiResponse } from '@/lib/api';

const TABS = [
  { id: 'auth', label: 'Auth', icon: '🔐' },
  { id: 'form4', label: 'Form 4', icon: '📊' },
  { id: 'tracking', label: 'Tracking', icon: '📁' },
  { id: 'watchlist', label: 'Watchlist', icon: '⭐' },
  { id: 'health', label: 'Health', icon: '💚' },
] as const;

type TabId = (typeof TABS)[number]['id'];

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<TabId>('auth');
  const [response, setResponse] = useState<ApiResponse | null>(null);

  const handleResponse = (res: ApiResponse) => {
    setResponse(res);
  };

  return (
    <main className="min-h-screen bg-zinc-950 text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center font-bold text-lg">
                S
              </div>
              <div>
                <h1 className="text-xl font-bold">SEC-Tracker</h1>
                <p className="text-xs text-zinc-400">API Testing Dashboard</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs text-zinc-500">
              <span className="px-2 py-1 bg-zinc-800 rounded">localhost:8080</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-12 gap-6 h-[calc(100vh-140px)]">
          {/* Left Column - Tabs + Panel */}
          <div className="col-span-5 flex flex-col">
            {/* Tabs */}
            <div className="flex gap-1 mb-4 p-1 bg-zinc-900 rounded-xl">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition ${
                    activeTab === tab.id
                      ? 'bg-zinc-700 text-white'
                      : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
                  }`}
                >
                  <span className="mr-1">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Panel Content */}
            <div className="flex-1 overflow-y-auto pr-2">
              {activeTab === 'auth' && <AuthPanel onResponse={handleResponse} />}
              {activeTab === 'form4' && <Form4Panel onResponse={handleResponse} />}
              {activeTab === 'tracking' && <TrackingPanel onResponse={handleResponse} />}
              {activeTab === 'watchlist' && <WatchlistPanel onResponse={handleResponse} />}
              {activeTab === 'health' && <HealthPanel onResponse={handleResponse} />}
            </div>
          </div>

          {/* Right Column - Response */}
          <div className="col-span-7 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-zinc-400">Response</h2>
              {response && (
                <button
                  onClick={() => setResponse(null)}
                  className="text-xs text-zinc-500 hover:text-zinc-300 transition"
                >
                  Clear
                </button>
              )}
            </div>
            <div className="flex-1 p-4 bg-zinc-900 rounded-xl border border-zinc-800 overflow-hidden">
              <ResponseViewer response={response} />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
