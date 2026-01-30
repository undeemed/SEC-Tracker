'use client';

import { ApiResponse } from '@/lib/api';

interface ResponseViewerProps {
  response: ApiResponse | null;
}

export default function ResponseViewer({ response }: ResponseViewerProps) {
  if (!response) {
    return (
      <div className="h-full flex items-center justify-center text-zinc-500">
        <p>Response will appear here</p>
      </div>
    );
  }

  const isSuccess = response.status >= 200 && response.status < 300;
  const content = response.error || response.data;

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-4 mb-3">
        <span
          className={`px-2 py-1 rounded text-xs font-semibold ${
            isSuccess ? 'bg-emerald-600' : 'bg-red-600'
          }`}
        >
          {response.status || 'ERR'}
        </span>
        <span className="text-xs text-zinc-400">{response.timing}ms</span>
      </div>
      <div className="flex-1 overflow-auto">
        <pre className="text-sm text-zinc-300 font-mono whitespace-pre-wrap break-words">
          {JSON.stringify(content, null, 2)}
        </pre>
      </div>
    </div>
  );
}
