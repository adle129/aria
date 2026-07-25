/** Format millisecond duration for RFQ timing UI (zh-CN). */
export function formatDurationMs(ms: number | null | undefined): string | null {
  if (ms == null || !Number.isFinite(ms) || ms < 0) return null;
  const totalSec = Math.round(ms / 1000);
  if (totalSec < 60) return `${totalSec}秒`;
  const minutes = Math.floor(totalSec / 60);
  const seconds = totalSec % 60;
  if (minutes < 60) {
    return seconds > 0 ? `${minutes}分${seconds}秒` : `${minutes}分`;
  }
  const hours = Math.floor(minutes / 60);
  const remMin = minutes % 60;
  return remMin > 0 ? `${hours}小时${remMin}分` : `${hours}小时`;
}

/** 「排队 X · 解析 Y」；缺省一侧则省略。 */
export function formatTaskTimingLine(opts: {
  queueWaitMs?: number | null;
  runMs?: number | null;
  /** When true: 「已等待 / 解析已进行」 */
  live?: boolean;
}): string | null {
  const queueLabel = opts.live ? "已等待" : "排队";
  const runLabel = opts.live ? "解析已进行" : "解析";
  const parts: string[] = [];
  const q = formatDurationMs(opts.queueWaitMs);
  const r = formatDurationMs(opts.runMs);
  if (q) parts.push(`${queueLabel} ${q}`);
  if (r) parts.push(`${runLabel} ${r}`);
  return parts.length > 0 ? parts.join(" · ") : null;
}
