import { parseApiTimestamp } from "@/lib/apiTime";

export const PROCESSING_STATUS_LABELS: Record<string, string> = {
  queued: "排队等待中",
  pending: "等待处理",
  parsing: "解析中",
  dimension_review: "等待基准维度勾选",
  retrieving: "检索相似项目",
  generating: "生成对比矩阵",
  cancelling: "正在取消",
  cancelled: "已取消",
  completed: "分析完成",
  failed: "分析失败",
};

/** Soft tag colors — avoid saturated Ant Design defaults. */
export const PROCESSING_STATUS_TAG_STYLE: Record<string, { color: string; background: string; borderColor: string }> = {
  queued: { color: "#5B7C99", background: "#F0F5FA", borderColor: "#D6E4F0" },
  pending: { color: "#5B7C99", background: "#F0F5FA", borderColor: "#D6E4F0" },
  parsing: { color: "#5B7C99", background: "#F0F5FA", borderColor: "#D6E4F0" },
  retrieving: { color: "#5B7C99", background: "#F0F5FA", borderColor: "#D6E4F0" },
  generating: { color: "#5B7C99", background: "#F0F5FA", borderColor: "#D6E4F0" },
  cancelling: { color: "#8C6D3F", background: "#FBF6EB", borderColor: "#EDE0C4" },
  cancelled: { color: "#666666", background: "#F5F5F5", borderColor: "#E8E8E8" },
  dimension_review: { color: "#A67C2D", background: "#FBF6EB", borderColor: "#EDE0C4" },
  completed: { color: "#3D7A5A", background: "#EEF6F1", borderColor: "#CDE5D8" },
  failed: { color: "#B33A3A", background: "#FBF0F0", borderColor: "#E8C9C9" },
};

const IN_FLIGHT_STATUSES = new Set([
  "queued",
  "pending",
  "parsing",
  "retrieving",
  "generating",
  "cancelling",
]);

export type InboxFilterKey = "all" | "in_progress" | "done" | "failed";

const INBOX_IN_PROGRESS_STATUSES = new Set([
  ...IN_FLIGHT_STATUSES,
  "dimension_review",
]);

export function matchesInboxFilter(status: string, filter: InboxFilterKey): boolean {
  if (filter === "all") return true;
  if (filter === "failed") return status === "failed" || status === "cancelled";
  if (filter === "done") return status === "completed";
  if (filter === "in_progress") return INBOX_IN_PROGRESS_STATUSES.has(status);
  return false;
}

export function getProcessingStatusTagColor(
  status: string,
): "default" | "processing" | "warning" | "success" | "error" {
  if (status === "failed") return "error";
  if (status === "cancelled") return "default";
  if (status === "completed") return "success";
  if (status === "dimension_review") return "warning";
  if (status === "cancelling") return "warning";
  if (IN_FLIGHT_STATUSES.has(status)) return "processing";
  return "default";
}

export function getProcessingStatusTagStyle(status: string) {
  return (
    PROCESSING_STATUS_TAG_STYLE[status] ?? {
      color: "#666666",
      background: "#F5F5F5",
      borderColor: "#E8E8E8",
    }
  );
}

export function formatTaskListTime(createdAt?: string): string {
  const then = parseApiTimestamp(createdAt);
  if (Number.isNaN(then)) return "—";
  return new Date(then).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/** Human-friendly relative time for list scanning. */
export function formatRelativeTime(createdAt?: string, nowMs: number = Date.now()): string {
  const then = parseApiTimestamp(createdAt);
  if (Number.isNaN(then)) return "—";
  const diffSec = Math.max(0, Math.floor((nowMs - then) / 1000));
  if (diffSec < 60) return "刚刚";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} 分钟前`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} 小时前`;
  if (diffSec < 86400 * 7) return `${Math.floor(diffSec / 86400)} 天前`;
  return formatTaskListTime(createdAt);
}

export function formatProcessingStatus(status: string): string {
  return PROCESSING_STATUS_LABELS[status] ?? status;
}

export function formatTaskListStatus(task: {
  processing_status: string;
  status_message?: string | null;
}): string {
  const message = task.status_message?.trim();
  if (message && IN_FLIGHT_STATUSES.has(task.processing_status)) {
    return message.replace(/\.\.\.$/, "");
  }
  return formatProcessingStatus(task.processing_status);
}

export function formatRecentTaskLabel(task: {
  task_id: string;
  file_name: string;
  processing_status: string;
  status_message?: string | null;
  created_at?: string;
}): string {
  const shortId = task.task_id.slice(0, 8);
  const then = parseApiTimestamp(task.created_at);
  const time = !Number.isNaN(then)
    ? new Date(then).toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      })
    : "";
  return `${task.file_name} · ${formatTaskListStatus(task)} · ${shortId}${
    time ? ` · ${time}` : ""
  }`;
}
