import axios from "axios";

const baseURL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL,
  timeout: 120000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const msg =
      error.response?.data?.msg ||
      error.message ||
      "请求失败，请稍后重试";
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
}

export async function fetchHealth(): Promise<HealthData> {
  const { data } = await apiClient.get<HealthData>("/health");
  return data;
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
