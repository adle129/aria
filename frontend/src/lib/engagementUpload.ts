/** Whether multipart upload needs engagement_id (loose files, not ZIP). */
export function uploadNeedsEngagementId(fileNames: string[]): boolean {
  if (!fileNames.length) return false;
  return !fileNames.some((n) => n.toLowerCase().endsWith(".zip"));
}
