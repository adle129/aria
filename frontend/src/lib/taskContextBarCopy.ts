/**
 * R1-PERF11: TaskContextBar copy for non-/rfq quoting pages (plan §5.3).
 */

const MACHINE_RUNNING = new Set([
  "queued",
  "pending",
  "parsing",
  "retrieving",
  "generating",
  "cancelling",
]);

export function isMachineRunningStatus(status: string): boolean {
  return MACHINE_RUNNING.has(status);
}

/** Tag label: human-review must read differently from "machine running". */
export function formatContextBarTagLabel(processingStatus: string): string {
  if (processingStatus === "dimension_review") return "待您确认";
  if (processingStatus === "queued" || processingStatus === "pending") return "排队中";
  if (processingStatus === "parsing") return "解析中";
  if (processingStatus === "retrieving" || processingStatus === "generating") {
    return "生成对比表中";
  }
  if (processingStatus === "cancelling") return "正在取消";
  if (processingStatus === "completed") return "分析完成";
  if (processingStatus === "failed") return "分析失败";
  if (processingStatus === "cancelled") return "已取消";
  return processingStatus;
}

/** One-line headline:「某某 RFQ 正在排队/解析/待确认」*/
export function formatContextBarHeadline(opts: {
  fileName?: string | null;
  processingStatus: string;
  queuePosition?: number | null;
}): string {
  const name = (opts.fileName || "RFQ").trim() || "RFQ";
  const status = opts.processingStatus;
  if (status === "dimension_review") {
    return `${name} 待您确认基准维度`;
  }
  if (status === "queued" || status === "pending") {
    const pos =
      opts.queuePosition != null && opts.queuePosition > 0
        ? `（第 ${opts.queuePosition} 位）`
        : "";
    return `${name} 正在排队${pos}`;
  }
  if (status === "parsing") {
    return `${name} 正在解析`;
  }
  if (status === "retrieving" || status === "generating") {
    return `${name} 正在生成对比表`;
  }
  if (status === "cancelling") {
    return `${name} 正在取消`;
  }
  if (status === "completed") {
    return `${name} 分析已完成`;
  }
  if (status === "failed") {
    return `${name} 分析失败`;
  }
  if (status === "cancelled") {
    return `${name} 已取消`;
  }
  return `${name} · ${formatContextBarTagLabel(status)}`;
}

export function formatContextBarQueueHint(opts: {
  processingStatus: string;
  queuePosition?: number | null;
  estimatedWaitSeconds?: number | null;
}): string | null {
  const queued =
    opts.processingStatus === "queued" || opts.processingStatus === "pending";
  if (!queued) return null;
  const pos =
    opts.queuePosition != null && opts.queuePosition > 0
      ? `第 ${opts.queuePosition} 位`
      : null;
  const eta =
    opts.estimatedWaitSeconds != null && opts.estimatedWaitSeconds > 0
      ? `预计还需约 ${Math.ceil(opts.estimatedWaitSeconds / 60)} 分钟`
      : null;
  if (pos && eta) return `排队中：${pos} · ${eta}`;
  if (pos) return `排队中：${pos}`;
  if (eta) return eta;
  return null;
}

export function shouldPollContextBarStatus(processingStatus: string): boolean {
  return isMachineRunningStatus(processingStatus);
}

export function contextBarOpenLabel(processingStatus: string): string {
  if (processingStatus === "dimension_review") return "前往确认维度";
  if (isMachineRunningStatus(processingStatus)) return "查看进度";
  return "在 RFQ 分析中打开";
}
