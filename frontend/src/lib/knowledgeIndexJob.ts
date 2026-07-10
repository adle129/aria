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
  validating: "校验暂存索引",
  switching: "切换生效版本",
  finalizing: "写入结果",
  completed: "索引完成",
  cancelled: "已取消",
};

export interface KnowledgeIndexFailure {
  path: string;
  error: string;
}

export interface KnowledgeIndexFailureGuidance {
  itemName: string;
  reason: string;
  impact: string;
  action: string;
}

export function getKnowledgeIndexFailureGuidance(
  failure: KnowledgeIndexFailure,
): KnowledgeIndexFailureGuidance {
  const itemName =
    failure.path.split(/[\\/]/).filter(Boolean).at(-1) ?? "未知项目";
  const reason = failure.error || "文档处理失败";

  if (/未找到\s*RFQ|缺少\s*RFQ/i.test(reason)) {
    return {
      itemName,
      reason,
      impact: "该项目未进入本次生效索引，无法参与 RFQ 相似检索与历史对标。",
      action:
        "请补充可正常打开的 RFQ .doc/.docx 文件；重新上传同一项目时勾选“替换同 ID 项目”，然后再次更新索引。",
    };
  }

  if (/解析失败|无法解析|格式/i.test(reason)) {
    return {
      itemName,
      reason,
      impact: "该文件或项目未进入本次生效索引，其他处理成功的项目不受影响。",
      action:
        "请确认文件未损坏且格式受支持，修复后重新上传；同 ID 项目需选择替换，然后再次更新索引。",
    };
  }

  return {
    itemName,
    reason,
    impact: "该文件或项目未进入本次生效索引，其他处理成功的项目不受影响。",
    action:
      "请根据失败原因修复资料后重新上传；同 ID 项目需选择替换，然后再次更新索引。若仍失败，请将项目名称和失败原因提供给管理员。",
  };
}
