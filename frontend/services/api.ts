import axios from "axios";

export const BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8007").replace(/\/$/, ''); // Remove trailing slash

// Safe URL joining helper - prevents double slashes
export const joinUrl = (base: string, path: string): string => {
  const cleanBase = base.replace(/\/$/, '');
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${cleanBase}${cleanPath}`;
};

// Debug log what URL is being used
console.log("🔧 DEBUG: NEXT_PUBLIC_API_URL =", process.env.NEXT_PUBLIC_API_URL);
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

const clearLocalAuth = () => {
  try {
    localStorage.removeItem("auth-storage");
  } catch {
    // no-op
  }
  setAuthToken(null);
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

// If backend says token/user is invalid (for example user deleted),
// force logout and route to login page.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const requestUrl: string = error?.config?.url || "";
    const isAuthEndpoint =
      requestUrl.includes("/api/auth/login") ||
      requestUrl.includes("/api/auth/register") ||
      requestUrl.includes("/api/auth/refresh");

    if (status === 401 && !isAuthEndpoint && typeof window !== "undefined") {
      clearLocalAuth();
      if (window.location.pathname !== "/login") {
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.replace(`/login?next=${next}`);
      }
    }

    return Promise.reject(error);
  }
);
