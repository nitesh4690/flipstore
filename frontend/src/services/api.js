import axios from "axios";

/**
 * Central Axios instance for the whole app.
 *
 * - baseURL comes from .env (VITE_API_URL), falling back to the Vite proxy.
 * - Request interceptor attaches the JWT stored after login.
 * - Response interceptor normalizes errors to `Error(message)` where message
 *   is the backend envelope's `message` field, and handles expired tokens.
 */

const baseURL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");
const TOKEN_KEY = "access_token";

const api = axios.create({
  baseURL: baseURL ? `${baseURL}/api` : "/api",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const message =
      error.response?.data?.message || error.message || "Something went wrong";

    if (status === 401) {
      // Expired/invalid token: clear it and send the user to login.
      setToken(null);
      const { pathname, search } = window.location;
      if (!pathname.startsWith("/login")) {
        const next = encodeURIComponent(`${pathname}${search}`);
        window.location.assign(`/login?next=${next}`);
      }
    }

    return Promise.reject(new Error(message));
  },
);

export default api;
