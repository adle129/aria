import type { DimensionDraftItem } from "@/types/task";

export type ReviewTier = "auto_include" | "needs_review" | "auto_exclude";

export interface DimensionEvidence {
  rfq_section?: string;
  rfq_section_title?: string;
  matched_keyword?: string;
  snippet?: string;
  source_ref?: string;
}

export interface ReviewSummary {
  total: number;
  auto_include: number;
  needs_review: number;
  auto_exclude: number;
}

const MATCH_LABELS: Record<string, string> = {
  keywords: "关键词匹配",
  module_scope: "模块范围推断",
  llm: "AI 语义匹配",
  none: "—",
};

export function inferReviewTier(item: DimensionDraftItem): ReviewTier {
  if (item.review_tier) {
    return item.review_tier;
  }
  const meta = inferMatchMeta(item);
  if (meta.match_type === "module_scope") return "needs_review";
  if (meta.match_type === "keywords") return "auto_include";
  if (item.confidence === "low" && meta.match_type !== "none") return "needs_review";
  if (item.in_scope) return "needs_review";
  return "auto_exclude";
}

export function inferMatchMeta(item: DimensionDraftItem): {
  match_type: string;
  source_label: string;
} {
  if (item.match_type) {
    return {
      match_type: item.match_type,
      source_label: item.source_label || MATCH_LABELS[item.match_type] || "—",
    };
  }
  const ref = item.source_ref;
  if (ref === "keywords") {
    return { match_type: "keywords", source_label: MATCH_LABELS.keywords };
  }
  if (ref === "module_scope") {
    return { match_type: "module_scope", source_label: MATCH_LABELS.module_scope };
  }
  if (ref && String(ref).startsWith("RFQ")) {
    return { match_type: "llm", source_label: MATCH_LABELS.llm };
  }
  return { match_type: "none", source_label: MATCH_LABELS.none };
}

export function computeReviewSummary(items: DimensionDraftItem[]): ReviewSummary {
  const summary: ReviewSummary = {
    total: items.length,
    auto_include: 0,
    needs_review: 0,
    auto_exclude: 0,
  };
  for (const item of items) {
    const tier = inferReviewTier(item);
    summary[tier] += 1;
  }
  return summary;
}

export function formatEvidenceLine(item: DimensionDraftItem): string {
  return resolveEvidenceDisplay(item).summaryLine;
}

export interface EvidenceDisplay {
  section?: string;
  chapterTitle?: string;
  matchedKeyword?: string;
  snippet?: string;
  summaryLine: string;
  subLine?: string;
}

export function resolveEvidenceDisplay(item: DimensionDraftItem): EvidenceDisplay {
  const ev = item.evidence ?? {};
  let section = ev.rfq_section;
  let chapterTitle = ev.rfq_section_title;
  const matchedKeyword = ev.matched_keyword;
  const snippet = ev.snippet;
  const ref = (item.source_ref || "").trim();

  if (ref) {
    const secInRef = ref.match(/§([^\s·]+)/);
    if (!section && secInRef?.[1]) section = secInRef[1];
    if (!chapterTitle) {
      const afterRfq = ref.replace(/^RFQ\s*/i, "").trim();
      const dotParts = afterRfq.split("·").map((p) => p.trim()).filter(Boolean);
      if (dotParts.length >= 2) {
        chapterTitle = dotParts[dotParts.length - 1];
      } else if (afterRfq && !afterRfq.startsWith("§")) {
        chapterTitle = afterRfq.replace(/^§[^\s·]+\s*/, "").trim() || afterRfq;
      }
    }
  }

  const titleParts: string[] = [];
  if (section) titleParts.push(`§${section}`);
  if (chapterTitle) titleParts.push(chapterTitle);

  let summaryLine: string;
  if (titleParts.length) {
    summaryLine = titleParts.join(" ");
  } else if (matchedKeyword) {
    summaryLine = `关键词「${matchedKeyword}」`;
  } else if (snippet) {
    summaryLine = snippet.length > 60 ? `${snippet.slice(0, 60)}…` : snippet;
  } else {
    summaryLine = ref || "—";
  }

  let subLine: string | undefined;
  if (matchedKeyword && chapterTitle) {
    subLine = `关键词「${matchedKeyword}」`;
  } else if (snippet && titleParts.length) {
    subLine = snippet.length > 48 ? `${snippet.slice(0, 48)}…` : snippet;
  }

  return { section, chapterTitle, matchedKeyword, snippet, summaryLine, subLine };
}

export function modulesRequiringReview(
  items: DimensionDraftItem[],
): Set<string> {
  const modules = new Set<string>();
  for (const item of items) {
    if (inferReviewTier(item) === "needs_review") {
      modules.add(item.module || "Other");
    }
  }
  return modules;
}

export function modulesWithInScope(items: DimensionDraftItem[]): Set<string> {
  const modules = new Set<string>();
  for (const item of items) {
    if (item.in_scope) {
      modules.add(item.module || "Other");
    }
  }
  for (const item of items) {
    if (item.custom && item.in_scope) {
      modules.add("Custom");
    }
  }
  return modules;
}

export function needsReviewItems(items: DimensionDraftItem[]): DimensionDraftItem[] {
  return items.filter((i) => inferReviewTier(i) === "needs_review" && i.in_scope);
}

export function matchTypeTagColor(matchType: string): string {
  if (matchType === "keywords") return "green";
  if (matchType === "module_scope") return "orange";
  if (matchType === "llm") return "blue";
  return "default";
}

const TIER_LABELS: Record<ReviewTier, string> = {
  auto_include: "自动纳入",
  needs_review: "待确认",
  auto_exclude: "已排除",
};

export function tierLabel(tier: ReviewTier): string {
  return TIER_LABELS[tier];
}

export function tierTagColor(tier: ReviewTier): string {
  if (tier === "auto_include") return "green";
  if (tier === "needs_review") return "orange";
  return "default";
}

/** Rows visible in review mode: included, pending manual review, or system-recommended auto-include. */
export function moduleReviewTableItems(items: DimensionDraftItem[]): DimensionDraftItem[] {
  return items.filter((i) => {
    if (i.in_scope) return true;
    const tier = inferReviewTier(i);
    return tier === "needs_review" || tier === "auto_include";
  });
}

function moduleHasReviewContent(items: DimensionDraftItem[]): boolean {
  return items.some((i) => {
    if (i.in_scope) return true;
    const tier = inferReviewTier(i);
    return tier === "needs_review" || tier === "auto_include";
  });
}

export type ModuleViewFilter = "review" | "all";

export function moduleMatchesFilter(
  items: DimensionDraftItem[],
  filter: ModuleViewFilter,
): boolean {
  if (items.length === 0) return false;
  if (filter === "all") return true;
  return moduleHasReviewContent(items);
}

export function moduleTableItems(
  items: DimensionDraftItem[],
  filter: ModuleViewFilter,
): DimensionDraftItem[] {
  if (filter === "all") return items;
  return moduleReviewTableItems(items);
}

export function countModulesForFilter(
  grouped: Map<string, DimensionDraftItem[]>,
  filter: ModuleViewFilter,
): number {
  let count = 0;
  for (const moduleItems of grouped.values()) {
    if (moduleMatchesFilter(moduleItems, filter)) count += 1;
  }
  return count;
}

/** Human-readable module status for review cards (counts match visible rows). */
export function formatModuleStatusLabel(
  items: DimensionDraftItem[],
  acknowledgedIds?: ReadonlySet<string>,
): string {
  const acked = acknowledgedIds ?? new Set<string>();
  const inScope = items.filter((i) => i.in_scope);
  const pendingReview = items.filter(
    (i) => inferReviewTier(i) === "needs_review" && !acked.has(i.dimension_id) && i.in_scope,
  );
  const suggestedAutoInclude = items.filter(
    (i) => inferReviewTier(i) === "auto_include" && !i.in_scope,
  );
  if (inScope.length === 0 && pendingReview.length === 0 && suggestedAutoInclude.length === 0) {
    return "系统判断：不需要介入";
  }
  const parts: string[] = [];
  if (inScope.length > 0) {
    parts.push(`已纳入 ${inScope.length} 项`);
    const autoIncluded = inScope.filter((i) => inferReviewTier(i) === "auto_include").length;
    if (autoIncluded > 0) {
      parts.push(`${autoIncluded} 项自动纳入`);
    }
  }
  if (suggestedAutoInclude.length > 0) {
    parts.push(`${suggestedAutoInclude.length} 项系统推荐纳入`);
  }
  if (pendingReview.length > 0) {
    parts.push(`${pendingReview.length} 项待确认`);
  }
  return parts.join(" · ");
}

export function displayTierForItem(
  item: DimensionDraftItem,
  acknowledgedIds: ReadonlySet<string>,
): { label: string; color: string } {
  const tier = inferReviewTier(item);
  if (tier === "needs_review" && acknowledgedIds.has(item.dimension_id)) {
    return { label: "已确认", color: "blue" };
  }
  return { label: tierLabel(tier), color: tierTagColor(tier) };
}
