const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export interface ApiResponse<T = unknown> {
  data?: T;
  error?: string;
  status: number;
  timing: number;
}

function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  
  const token = localStorage.getItem('sec_token');
  const apiKey = localStorage.getItem('sec_api_key');
  
  if (apiKey) {
    return { 'X-API-Key': apiKey };
  }
  if (token) {
    return { 'Authorization': `Bearer ${token}` };
  }
  return {};
}

export async function apiCall<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const start = performance.now();
  
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
        ...options.headers,
      },
    });
    
    const timing = Math.round(performance.now() - start);
    
    if (response.status === 204) {
      return { status: response.status, timing };
    }
    
    const data = await response.json();
    
    if (!response.ok) {
      return { error: data.detail || data.message || 'Request failed', status: response.status, timing };
    }
    
    return { data, status: response.status, timing };
  } catch (err) {
    const timing = Math.round(performance.now() - start);
    return { error: String(err), status: 0, timing };
  }
}

// Auth endpoints
export const auth = {
  register: (email: string, password: string) =>
    apiCall('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  
  login: async (email: string, password: string) => {
    const result = await apiCall<{ access_token: string; refresh_token: string }>(
      '/api/v1/auth/login',
      { method: 'POST', body: JSON.stringify({ email, password }) }
    );
    if (result.data?.access_token) {
      localStorage.setItem('sec_token', result.data.access_token);
      localStorage.setItem('sec_refresh', result.data.refresh_token);
    }
    return result;
  },
  
  logout: () => {
    localStorage.removeItem('sec_token');
    localStorage.removeItem('sec_refresh');
    localStorage.removeItem('sec_api_key');
  },
  
  me: () => apiCall('/api/v1/auth/me'),
  
  generateApiKey: async () => {
    const result = await apiCall<{ api_key: string }>('/api/v1/auth/api-key', { method: 'POST' });
    if (result.data?.api_key) {
      localStorage.setItem('sec_api_key', result.data.api_key);
    }
    return result;
  },
  
  revokeApiKey: async () => {
    const result = await apiCall('/api/v1/auth/api-key', { method: 'DELETE' });
    localStorage.removeItem('sec_api_key');
    return result;
  },
};

// Form4 endpoints
export const form4 = {
  getCompany: (ticker: string, params?: { days?: number; count?: number; hide_planned?: boolean }) => {
    const query = new URLSearchParams();
    if (params?.days) query.set('days', String(params.days));
    if (params?.count) query.set('count', String(params.count));
    if (params?.hide_planned) query.set('hide_planned', 'true');
    const qs = query.toString();
    return apiCall(`/api/v1/form4/${ticker}${qs ? '?' + qs : ''}`);
  },
  
  getMarket: () => apiCall('/api/v1/form4/'),
};

// Tracking endpoints
export const tracking = {
  start: (ticker: string, forms: string[]) =>
    apiCall('/api/v1/track/', {
      method: 'POST',
      body: JSON.stringify({ ticker, forms }),
    }),
  
  getJob: (jobId: string) => apiCall(`/api/v1/track/job/${jobId}`),
  
  getHistory: (params?: { limit?: number; offset?: number; ticker?: string }) => {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    if (params?.ticker) query.set('ticker', params.ticker);
    const qs = query.toString();
    return apiCall(`/api/v1/track/history${qs ? '?' + qs : ''}`);
  },
};

// Watchlist endpoints
export const watchlist = {
  get: () => apiCall('/api/v1/watchlist/'),
  
  add: (ticker: string) =>
    apiCall('/api/v1/watchlist/', {
      method: 'POST',
      body: JSON.stringify({ ticker }),
    }),
  
  remove: (ticker: string) =>
    apiCall(`/api/v1/watchlist/${ticker}`, { method: 'DELETE' }),
  
  search: (q: string, limit = 10) =>
    apiCall(`/api/v1/watchlist/search?q=${encodeURIComponent(q)}&limit=${limit}`),
};

// Health endpoint
export const health = {
  check: () => apiCall('/api/v1/health'),
};
