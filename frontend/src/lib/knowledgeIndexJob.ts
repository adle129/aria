export type KnowledgeIndexJobStatus =
  | "queued"
  | "running"
  | "cancelling"
  | "completed"
  | "failed"
  | "cancelled";

export const ACTIVE_INDEX_JOB_STATUSES = new Set<KnowledgeIndexJobStatus>([
  "queued",
  "running",
  "cancelling",
]);

export const INDEX_JOB_STATUS_LABEL: Record<KnowledgeIndexJobStatus, string> = {
  queued: "排队中",
  running: "索引中",
  cancelling: "正在取消",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

export const INDEX_JOB_PHASE_LABEL: Record<string, string> = {
  queued: "等待 worker",
  scanning: "扫描项目包",
  parsing: "解析文档",
  embedding: "生成向量并写入索引",
  finalizing: "写入结果",
  completed: "索引完成",
  cancelled: "已取消",
};
