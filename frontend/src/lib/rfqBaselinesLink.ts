export function resolveEngagementId(
  row: Record<string, unknown>,
  similarProjects?: Array<Record<string, unknown>>,
): string | null {
  if (row.engagement_id) return String(row.engagement_id);
  const rowName = String(row.project_name || "");
  const hit = (similarProjects || []).find((s) => {
    const meta = s.metadata as Record<string, unknown> | undefined;
    return String(meta?.project_name || s.project_name || "") === rowName;
  });
  const meta = hit?.metadata as Record<string, unknown> | undefined;
  return meta?.engagement_id ? String(meta.engagement_id) : null;
}

/**
 * Man-day baselines are viewed in the RFQ page drawer only (not /knowledge).
 * Kept for call-site clarity / tests — always null.
 */
export function buildBaselinesKnowledgeHref(_engagementId: string): null {
  return null;
}

export function resolveProjectBaselinesEngagementIds(
  projects: Array<Record<string, unknown>>,
  similarProjects?: Array<Record<string, unknown>>,
): (string | null)[] {
  return projects.map((p) => resolveEngagementId(p, similarProjects));
}
