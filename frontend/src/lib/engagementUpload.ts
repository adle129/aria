/** Whether multipart upload needs engagement_id (loose files, not ZIP). */
export function uploadNeedsEngagementId(fileNames: string[]): boolean {
  if (!fileNames.length) return false;
  return !fileNames.some((n) => n.toLowerCase().endsWith(".zip"));
}

/** 金/银/铜分级 — 对齐 R1 验收说明 §2.1、rag-design §11.4.1 */
export function engagementTier(missing: string[] | undefined): "金级" | "银级" | "铜级" {
  const m = missing ?? [];
  if (m.length === 0) return "金级";
  if (m.length === 1 && m[0] === "quote_manpower") return "银级";
  return "铜级";
}

/** 缺件对后续里程碑自动化的影响 — 对齐客户版验收说明 */
export function missingAutomationImpact(missing: string[] | undefined): string[] {
  const m = missing ?? [];
  const lines: string[] = [];
  if (m.includes("rfq")) lines.push("缺 RFQ：无法参与 RFQ 相似检索与对标");
  if (m.includes("qa")) lines.push("缺 Q&A：第三期 Q&A 自动生成不可用（M4）");
  if (m.includes("quote_manpower")) lines.push("缺人力报价 Excel：第二期报价 Excel 自动生成不可用（M3）");
  return lines;
}