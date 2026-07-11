/** Whether multipart upload needs engagement_id (loose files, not ZIP). */
export function uploadNeedsEngagementId(fileNames: string[]): boolean {
  if (!fileNames.length) return false;
  return !fileNames.some((n) => n.toLowerCase().endsWith(".zip"));
}

export const MAX_UPLOAD_FILE_BYTES = 100 * 1024 * 1024;
export const MAX_ENGAGEMENT_ZIPS = 5;

export interface UploadCandidate {
  name: string;
  size: number;
}

export function validateEngagementUpload(
  files: UploadCandidate[],
): string | null {
  const zipCount = files.filter((file) =>
    file.name.toLowerCase().endsWith(".zip"),
  ).length;
  if (zipCount && zipCount !== files.length) {
    return "ZIP 与散文件不可在同一次上传中混传";
  }
  if (zipCount > MAX_ENGAGEMENT_ZIPS) {
    return `单次最多上传 ${MAX_ENGAGEMENT_ZIPS} 个项目 ZIP`;
  }
  const oversized = files.find(
    (file) => file.size > MAX_UPLOAD_FILE_BYTES,
  );
  if (oversized) {
    return `${oversized.name} 超过 100MB 上传限制`;
  }
  return null;
}

export type UploadPackOutcome = "failed" | "incomplete" | "indexable";

export interface UploadPackStatusView {
  outcome: UploadPackOutcome;
  label: string;
  color: "error" | "warning" | "success";
}

/** Map API pack flags to customer-facing upload status. */
export function formatUploadPackStatus(pack: {
  stored: boolean;
  indexable: boolean;
  missing?: string[] | null;
}): UploadPackStatusView {
  if (!pack.stored) {
    return { outcome: "failed", label: "上传失败", color: "error" };
  }
  if (pack.indexable && !(pack.missing?.length)) {
    return { outcome: "indexable", label: "已上传·可索引", color: "success" };
  }
  if (pack.indexable) {
    return {
      outcome: "incomplete",
      label: "已上传·可索引（资料不完整）",
      color: "warning",
    };
  }
  return { outcome: "incomplete", label: "已上传·资料不完整", color: "warning" };
}

export function summarizeUploadPacks(
  packs: Array<{
    stored: boolean;
    indexable: boolean;
    missing?: string[] | null;
  }>,
): { failed: number; incomplete: number; indexable: number; stored: number } {
  let failed = 0;
  let incomplete = 0;
  let indexable = 0;
  let stored = 0;
  for (const pack of packs) {
    const view = formatUploadPackStatus(pack);
    if (view.outcome === "failed") failed += 1;
    else if (view.outcome === "indexable") indexable += 1;
    else incomplete += 1;
    if (pack.stored) stored += 1;
  }
  return { failed, incomplete, indexable, stored };
}
