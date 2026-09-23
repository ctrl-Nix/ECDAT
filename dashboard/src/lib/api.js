import axios from 'axios';

// Default to a same-origin '/api' path so the browser never makes a
// cross-origin request: the dashboard's nginx proxies '/api/*' to the backend
// over the internal Docker network (see dashboard/nginx.conf).
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ecdat_token');

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('ecdat_token');
      localStorage.removeItem('ecdat_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  },
);

export default api;
