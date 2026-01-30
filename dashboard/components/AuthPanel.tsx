'use client';

import { useState } from 'react';
import { auth } from '@/lib/api';
import { ApiResponse } from '@/lib/api';

interface AuthPanelProps {
  onResponse: (response: ApiResponse) => void;
}

export default function AuthPanel({ onResponse }: AuthPanelProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState<string | null>(null);

  const handleAction = async (action: string, fn: () => Promise<ApiResponse>) => {
    setLoading(action);
    const result = await fn();
    onResponse(result);
    setLoading(null);
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm text-zinc-400">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            placeholder="user@example.com"
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm text-zinc-400">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            placeholder="••••••••"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => handleAction('register', () => auth.register(email, password))}
          disabled={loading !== null}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg font-medium transition"
        >
          {loading === 'register' ? 'Registering...' : 'Register'}
        </button>
        <button
          onClick={() => handleAction('login', () => auth.login(email, password))}
          disabled={loading !== null}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg font-medium transition"
        >
          {loading === 'login' ? 'Logging in...' : 'Login'}
        </button>
      </div>

      <hr className="border-zinc-700" />

      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => handleAction('me', () => auth.me())}
          disabled={loading !== null}
          className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 rounded-lg font-medium transition"
        >
          {loading === 'me' ? 'Loading...' : 'Get Current User'}
        </button>
        <button
          onClick={() => {
            auth.logout();
            onResponse({ status: 200, timing: 0, data: { message: 'Logged out' } });
          }}
          className="px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg font-medium transition"
        >
          Logout (Clear Tokens)
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => handleAction('genKey', () => auth.generateApiKey())}
          disabled={loading !== null}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 rounded-lg font-medium transition"
        >
          {loading === 'genKey' ? 'Generating...' : 'Generate API Key'}
        </button>
        <button
          onClick={() => handleAction('revokeKey', () => auth.revokeApiKey())}
          disabled={loading !== null}
          className="px-4 py-2 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 rounded-lg font-medium transition"
        >
          {loading === 'revokeKey' ? 'Revoking...' : 'Revoke API Key'}
        </button>
      </div>
    </div>
  );
}
