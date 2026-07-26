/**
 * R1-PERF10: busy-hours banner + 429/503 action-area copy (plan §5.4).
 * Thresholds are frontend constants (documented); keep aligned with ops expectations.
 */

/** Show busy banner when queue position reaches this (1-based). */
export const RFQ_BUSY_QUEUE_POSITION_THRESHOLD = 3;

/** Show busy banner when ETA reaches this many seconds (10 minutes). */
export const RFQ_BUSY_ETA_SECONDS_THRESHOLD = 600;

/** Mirrors backend `task_max_queue_size` default for 429 copy. */
export const RFQ_TASK_MAX_QUEUE_SIZE_DEFAULT = 20;

export const RFQ_BUSY_HOURS_BANNER_MESSAGE =
  "现在使用的人较多。您的任务已安全排队；若不紧急，也可错开高峰再上传。";

export const RFQ_SEARCH_BUSY_503_MESSAGE =
  "当前计算资源繁忙，检索暂时不可用。请稍后再试；进行中的 RFQ 分析不受影响。";

export function shouldShowBusyHoursBanner(opts: {
  queuePosition?: number | null;
  estimatedWaitSeconds?: number | null;
}): boolean {
  const pos = opts.queuePosition;
  if (pos != null && pos >= RFQ_BUSY_QUEUE_POSITION_THRESHOLD) {
    return true;
  }
  const eta = opts.estimatedWaitSeconds;
  if (eta != null && eta >= RFQ_BUSY_ETA_SECONDS_THRESHOLD) {
    return true;
  }
  return false;
}

export function formatQueueFullActionMessage(opts: {
  queueDepth?: number | null;
  maxQueueSize?: number | null;
}): string {
  const depth = opts.queueDepth;
  const max = opts.maxQueueSize ?? RFQ_TASK_MAX_QUEUE_SIZE_DEFAULT;
  if (depth != null && depth > 0) {
    return `当前排队人数已满（${depth}/${max}）。请稍后再上传，或取消不再需要的任务后再试。`;
  }
  return `当前排队人数已满。请稍后再上传，或取消不再需要的任务后再试。`;
}

export type RfqActionErrorKind = "queue_full" | "search_busy" | "generic";

export function resolveActionAreaError(opts: {
  httpStatus?: number | null;
  queueDepth?: number | null;
  maxQueueSize?: number | null;
  fallbackMessage?: string | null;
}): { kind: RfqActionErrorKind; message: string } | null {
  const status = opts.httpStatus;
  if (status === 429) {
    return {
      kind: "queue_full",
      message: formatQueueFullActionMessage({
        queueDepth: opts.queueDepth,
        maxQueueSize: opts.maxQueueSize,
      }),
    };
  }
  if (status === 503) {
    return {
      kind: "search_busy",
      message: RFQ_SEARCH_BUSY_503_MESSAGE,
    };
  }
  if (opts.fallbackMessage?.trim()) {
    return { kind: "generic", message: opts.fallbackMessage.trim() };
  }
  return null;
}

/** Axios-like error shape → action-area payload (no toast required). */
export function actionAreaErrorFromAxios(err: unknown): {
  kind: RfqActionErrorKind;
  message: string;
} | null {
  const ax = err as {
    response?: {
      status?: number;
      data?: { msg?: string; queue_depth?: number; code?: number };
    };
    message?: string;
  };
  const status = ax.response?.status;
  const data = ax.response?.data;
  return resolveActionAreaError({
    httpStatus: status,
    queueDepth: data?.queue_depth,
    fallbackMessage: data?.msg || ax.message || null,
  });
}
