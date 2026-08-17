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
