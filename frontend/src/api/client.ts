import axios from "axios";

const baseURL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export const TOKEN_KEY = "aria_access_token";

export const apiClient = axios.create({
  baseURL,
  timeout: 120000,
});

export interface AuthUser {
  id: string;
  username: string;
  display_name: string;
  role: "quote_engineer" | "kb_admin";
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let authRedirectPending = false;

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const msg =
      error.response?.data?.msg ||
      error.message ||
      "请求失败，请稍后重试";
    if (
      status === 401 &&
      typeof window !== "undefined" &&
      !window.location.pathname.startsWith("/login") &&
      !authRedirectPending
    ) {
      authRedirectPending = true;
      setStoredToken(null);
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/login?next=${next}`;
      return Promise.reject(error);
    }
    if (typeof window !== "undefined") {
      import("antd").then(({ message }) => message.error(msg));
    }
    return Promise.reject(error);
  },
);

export interface HealthData {
  status: string;
  version: string;
  model: string;
  embedding_model: string;
  mock_llm: boolean;
  mock_rag: boolean;
  ollama_reachable: boolean;
  ollama_model_ready: boolean;
  embedding_model_ready: boolean;
  ollama_error?: string | null;
  kb_debug_enabled?: boolean;
  aria_ui_profile?: string;
  auth_enabled?: boolean;
}

export async function fetchHealth(): Promise<HealthData> {
  const { data } = await apiClient.get<HealthData>("/health");
  return data;
}

export async function login(username: string, password: string): Promise<LoginResult> {
  const { data } = await apiClient.post<{ code: number; data: LoginResult }>("/auth/login", {
    username,
    password,
  });
  return data.data;
}

export async function fetchMe(): Promise<AuthUser> {
  const { data } = await apiClient.get<{ code: number; data: AuthUser }>("/auth/me");
  return data.data;
}

/** Build absolute API URL for browser navigation (download links). */
export function buildApiUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (base.startsWith("/") && typeof window !== "undefined") {
    return `${window.location.origin}${base}${normalizedPath}`;
  }
  return `${base.replace(/\/$/, "")}${normalizedPath}`;
}

export const LAST_TASK_ID_KEY = "aria_last_task_id";
