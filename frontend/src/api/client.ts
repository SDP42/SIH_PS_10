import axios from 'axios';

const isLocalhost = typeof window !== 'undefined' && 
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

const BASE_URL = import.meta.env.VITE_API_BASE_URL || (isLocalhost ? 'http://localhost:8000' : '');

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const DEMO_AUTH_STORAGE_KEY = 'namaste_icd11_demo_auth';

apiClient.interceptors.request.use((config) => {
  const raw = localStorage.getItem(DEMO_AUTH_STORAGE_KEY);
  if (raw) {
    try {
      const { access_token } = JSON.parse(raw);
      if (access_token) {
        config.headers = config.headers || {};
        config.headers['Authorization'] = `Bearer ${access_token}`;
      }
    } catch {
      // ignore malformed stored session
    }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      return Promise.reject(error.response.data || error);
    }
    return Promise.reject(error);
  }
);

export default apiClient;
