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
