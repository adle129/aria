import type { DiskVolumeHealth } from "@/api/client";

export function formatCapacityBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
}

export function capacityAlert(
  volume?: DiskVolumeHealth | null,
): {
  type: "warning" | "error";
  message: string;
  description: string;
} | null {
  if (!volume?.warning && !volume?.write_protected) return null;
  const usage = volume.usage_percent.toFixed(1);
  const free = formatCapacityBytes(volume.free_bytes);
  if (volume.write_protected) {
    return {
      type: "error",
      message: "知识库数据盘已进入写保护",
      description: `当前使用率 ${usage}%，剩余 ${free}。上传和索引已暂停，现有检索与下载仍可使用。请清理或扩容后重试。`,
    };
  }
  return {
    type: "warning",
    message: "知识库数据盘空间即将不足",
    description: `当前使用率 ${usage}%，剩余 ${free}。建议尽快清理或扩容，避免上传和索引被暂停。`,
  };
}
