import axios from "axios";

declare module "axios" {
  export interface AxiosRequestConfig {
    silentError?: boolean;
    /** When true, show toast for task-not-found 404 (manual user action). */
    showError?: boolean;
  }
}

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
  expires_at: string;
  user: AuthUser;
}

export interface TokenRefreshResult {
  access_token: string;
  token_type: string;
  expires_at: string;
}

export interface UserDetail extends AuthUser {
  is_active: boolean;
  created_at: string | null;
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

function isTaskNotFoundError(status: number | undefined, msg: string, url: string): boolean {
  return (
    status === 404 &&
    msg === "任务 ID 不存在" &&
    /\/rfq\/tasks\/[^/?]+(\/(status|manpower-breakdown-preview))?$/.test(url)
  );
}

export function shouldShowApiError(
  status: number | undefined,
  msg: string,
  config: { silentError?: boolean; showError?: boolean; url?: string } | undefined,
): boolean {
  if (config?.silentError) return false;
  const url = config?.url ?? "";
  if (isTaskNotFoundError(status, msg, url) && !config?.showError) return false;
  return true;
}

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
    if (typeof window !== "undefined" && shouldShowApiError(status, msg, error.config)) {
      import("antd").then(({ message }) => message.error(msg));
    }
    return Promise.reject(error);
  },
);

export interface HealthData {
  status: string;
  version: string;
  deploy_sha?: string;
  packaged_at?: string | null;
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
  data_volume?: DiskVolumeHealth;
  temp_volume?: DiskVolumeHealth;
}

export interface DiskVolumeHealth {
  volume: string;
  total_bytes: number;
  used_bytes: number;
  free_bytes: number;
  usage_percent: number;
  warning: boolean;
  write_protected: boolean;
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

export async function refreshToken(): Promise<TokenRefreshResult> {
  const { data } = await apiClient.post<{ code: number; data: TokenRefreshResult }>("/auth/refresh");
  return data.data;
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await apiClient.post("/auth/change-password", {
    old_password: oldPassword,
    new_password: newPassword,
  });
}

export async function listUsers(): Promise<UserDetail[]> {
  const { data } = await apiClient.get<{ code: number; data: UserDetail[] }>("/auth/users");
  return data.data;
}

export async function createUser(payload: {
  username: string;
  password: string;
  display_name: string;
  role: string;
}): Promise<UserDetail> {
  const { data } = await apiClient.post<{ code: number; data: UserDetail }>("/auth/users", payload);
  return data.data;
}

export async function updateUser(
  userId: string,
  patch: { display_name?: string; role?: string; is_active?: boolean },
): Promise<UserDetail> {
  const { data } = await apiClient.patch<{ code: number; data: UserDetail }>(
    `/auth/users/${userId}`,
    patch,
  );
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

export function clearStoredTaskId(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(LAST_TASK_ID_KEY);
}

export async function retryTask(taskId: string): Promise<{ status: string }> {
  const { data } = await apiClient.post<{ code: number; data: { status: string } }>(
    `/rfq/tasks/${taskId}/retry`,
  );
  return data.data;
}

export async function deleteTask(taskId: string): Promise<void> {
  await apiClient.delete(`/rfq/tasks/${taskId}`);
}

export async function archiveTask(taskId: string): Promise<void> {
  await apiClient.patch(`/rfq/tasks/${taskId}/archive`);
}
