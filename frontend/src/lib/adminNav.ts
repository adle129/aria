/** Admin ops console IA labels + AI health one-liner (R1-CHG04 shell). */

import type { HealthData } from "@/api/client";

export const ADMIN_NAV_GROUP_LABEL = "平台管理";

export const ADMIN_NAV_LABELS = {
  overview: "管理首页",
  documents: "知识库",
  masterData: "客户与车型",
  users: "用户管理",
} as const;

/** Same gate as platform knowledge nav: auth off (dev) or kb_admin. */
export function canAccessAdminOpsNav(input: {
  authEnabled: boolean;
  isKbAdmin: boolean;
}): boolean {
  if (!input.authEnabled) return true;
  return input.isKbAdmin;
}

export function canAccessUserAdmin(input: {
  authEnabled: boolean;
  isKbAdmin: boolean;
}): boolean {
  return input.authEnabled && input.isKbAdmin;
}

export type AiHealthTone = "ok" | "warn" | "error" | "unknown";

export type AiHealthSummary = {
  tone: AiHealthTone;
  label: string;
  detail: string;
};

/** Single customer-facing AI availability line — not Token/usage. */
export function summarizeAiHealth(health: HealthData | null | undefined): AiHealthSummary {
  if (!health) {
    return {
      tone: "unknown",
      label: "AI 服务状态未知",
      detail: "未能读取健康检查，请稍后重试或联系运维。",
    };
  }
  if (health.mock_llm) {
    return {
      tone: "warn",
      label: "AI 为 Mock 模式",
      detail: "当前未连接真实本地模型；正式环境请关闭 MOCK_LLM。",
    };
  }
  if (!health.ollama_reachable) {
    return {
      tone: "error",
      label: "AI 服务不可用",
      detail: health.ollama_error || "本地模型服务未连接，报价解析与检索将受影响。",
    };
  }
  if (!health.ollama_model_ready) {
    return {
      tone: "warn",
      label: "模型未就绪",
      detail: `服务已连接，但模型 ${health.model || "—"} 尚未就绪。`,
    };
  }
  const embedOk = health.embedding_model_ready !== false;
  if (!embedOk) {
    return {
      tone: "warn",
      label: "向量模型未就绪",
      detail: `对话模型可用；Embedding（${health.embedding_model || "—"}）未就绪，知识库检索可能失败。`,
    };
  }
  return {
    tone: "ok",
    label: "AI 服务可用",
    detail: `模型 ${health.model} · Embedding ${health.embedding_model}`,
  };
}

export function aiHealthTagColor(tone: AiHealthTone): string {
  if (tone === "ok") return "success";
  if (tone === "warn") return "warning";
  if (tone === "error") return "error";
  return "default";
}
