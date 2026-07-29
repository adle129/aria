/** Helpers for R1-CHG08 module_source_summaries cache (quote source picker). */

export type ModuleSummaryStatus = "placeholder" | "hint" | "empty" | string;

export type ModuleSummaryCell = {
  bullets?: string[];
  status?: ModuleSummaryStatus;
  source?: string;
  keywords_used?: string[];
};

export type ModuleSourceSummaries = {
  mode?: string;
  note?: string;
  in_scope?: string[];
  by_engagement?: Record<string, Record<string, ModuleSummaryCell>>;
};

export function getModuleSummaryBullets(
  summaries: ModuleSourceSummaries | null | undefined,
  engagementId: string | null | undefined,
  functionKey: string,
): string[] {
  if (!summaries || !engagementId) return [];
  const cell = summaries.by_engagement?.[engagementId]?.[functionKey];
  const bullets = cell?.bullets;
  if (!Array.isArray(bullets)) return [];
  return bullets.map((b) => String(b).trim()).filter(Boolean).slice(0, 4);
}

export function getModuleSummaryStatus(
  summaries: ModuleSourceSummaries | null | undefined,
  engagementId: string | null | undefined,
  functionKey: string,
): ModuleSummaryStatus | null {
  if (!summaries || !engagementId) return null;
  return summaries.by_engagement?.[engagementId]?.[functionKey]?.status ?? null;
}
