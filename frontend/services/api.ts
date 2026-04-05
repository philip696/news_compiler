import axios from "axios";

export const BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, ''); // Remove trailing slash

// Safely join BASE_URL with a path to avoid double slashes
export const joinUrl = (basePath: string): string => {
  if (!basePath) return BASE_URL;
  // Remove leading slash from path if present to avoid double slash
  const cleanPath = basePath.startsWith('/') ? basePath.slice(1) : basePath;
  return `${BASE_URL}/${cleanPath}`;
};

// Debug log what URL is being used
console.log("🔧 DEBUG: NEXT_PUBLIC_API_BASE_URL =", process.env.NEXT_PUBLIC_API_BASE_URL);
console.log("🔧 DEBUG: Using BASE_URL =", BASE_URL);

export const api = axios.create({
  baseURL: BASE_URL
});

export const setAuthToken = (token: string | null) => {
  if (!token) {
    delete api.defaults.headers.common.Authorization;
    return;
  }
  api.defaults.headers.common.Authorization = `Bearer ${token}`;
};

// Add a request interceptor to ensure token is always sent
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth-storage");
  if (token) {
    try {
      const parsed = JSON.parse(token);
      if (parsed.state?.token) {
        config.headers.Authorization = `Bearer ${parsed.state.token}`;
      }
    } catch (e) {
      // Will use default headers if parsing fails
    }
  }
  return config;
});
