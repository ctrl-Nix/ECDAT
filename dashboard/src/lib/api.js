import axios from 'axios';

// Default to a same-origin '/api' path so the browser never makes a
// cross-origin request: the dashboard's nginx proxies '/api/*' to the backend
// over the internal Docker network (see dashboard/nginx.conf). This sidesteps
// CORS and the strict CSP (connect-src 'self'), and keeps the API key off the
// wire from the browser's perspective.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ecdat_token');
  const apiKey = import.meta.env.VITE_API_KEY || 'demo-key';

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  config.headers['X-API-Key'] = apiKey;

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 || error.response?.status === 403) {
      localStorage.removeItem('ecdat_token');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  },
);

export default api;
