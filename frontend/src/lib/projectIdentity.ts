/** Customer-facing labels for engagement identity (not technical jargon). */

export const PROJECT_ID_LABEL = "项目编号";

export const PROJECT_ID_TIP =
  "系统为每套历史资料生成的唯一编号。同客户、同车型可以有多套项目，靠编号区分；查找、对标、人天明细都认这个编号。";

export const PROJECT_DISPLAY_NAME_TIP =
  "给人看的名称，可以重复。真正区分项目请看项目编号。";

export const PROJECT_YEAR_TIP =
  "项目所属年份，便于列表筛选和区分多期项目。不是唯一编号。";

export function formatProjectIdLine(engagementId?: string | null): string | null {
  const id = (engagementId || "").trim();
  if (!id || id.startsWith("orphan:")) return null;
  return `${PROJECT_ID_LABEL} ${id}`;
}

export function matchesProjectKeyword(
  row: {
    engagement_id?: string;
    project_name?: string;
    customer?: string | null;
    vehicle_model?: string | null;
  },
  keyword: string,
): boolean {
  const q = keyword.trim().toLowerCase();
  if (!q) return true;
  const hay = [
    row.engagement_id,
    row.project_name,
    row.customer,
    row.vehicle_model,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return hay.includes(q);
}
