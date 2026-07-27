/** Nine quote Function Sheets + function_source_map helpers (R1-CHG03). */

import { resolveVehicleModel } from "@/lib/matrixProjectHeader";

export const QUOTE_FUNCTION_KEYS = [
  "PM",
  "BIW",
  "Interior",
  "GI",
  "Test validation",
  "Chassis",
  "CAE",
  "EE",
  "PS",
] as const;

export type QuoteFunctionKey = (typeof QUOTE_FUNCTION_KEYS)[number];

export type FunctionSourceMap = Record<QuoteFunctionKey, string | null>;

/** One column aligned with comparison matrix history projects. */
export type SourceCandidate = {
  /** Stable React/table column key */
  columnKey: string;
  /** Selectable only when present (persisted in function_source_map). */
  engagementId: string | null;
  projectName: string;
  customer?: string | null;
  vehicleModel?: string | null;
  similarityScore?: number | null;
};

export const QUOTE_FUNCTION_LABELS: Record<QuoteFunctionKey, string> = {
  PM: "PM",
  BIW: "BIW 白车身",
  Interior: "Interior 内外饰",
  GI: "GI",
  "Test validation": "Test validation",
  Chassis: "Chassis 底盘",
  CAE: "CAE",
  EE: "EE",
  PS: "PS",
};

export const QUOTE_FUNCTION_SHORT: Record<QuoteFunctionKey, string> = {
  PM: "PM",
  BIW: "BIW",
  Interior: "Interior",
  GI: "GI",
  "Test validation": "Test validation",
  Chassis: "Chassis",
  CAE: "CAE",
  EE: "EE",
  PS: "PS",
};

const ALIASES: Record<string, QuoteFunctionKey> = {
  pm: "PM",
  biw: "BIW",
  interior: "Interior",
  gi: "GI",
  "test validation": "Test validation",
  test_validation: "Test validation",
  chassis: "Chassis",
  classis: "Chassis",
  cae: "CAE",
  ee: "EE",
  ps: "PS",
};

/** Align with comparison matrix Top-N history columns. */
export const SOURCE_CANDIDATE_LIMIT = 3;

export function canonicalizeFunctionKey(raw: string): QuoteFunctionKey | null {
  const text = String(raw || "").trim();
  if (!text) return null;
  if ((QUOTE_FUNCTION_KEYS as readonly string[]).includes(text)) {
    return text as QuoteFunctionKey;
  }
  return ALIASES[text.toLowerCase()] ?? null;
}

export function emptyFunctionSourceMap(): FunctionSourceMap {
  return QUOTE_FUNCTION_KEYS.reduce((acc, key) => {
    acc[key] = null;
    return acc;
  }, {} as FunctionSourceMap);
}

export function resolveInScopeFunctions(
  rfqModules?: Record<string, unknown> | null,
): QuoteFunctionKey[] {
  const raw = (rfqModules?.functions_in_scope as unknown[]) || [];
  const seen = new Set<QuoteFunctionKey>();
  for (const item of raw) {
    const key = canonicalizeFunctionKey(String(item));
    if (key) seen.add(key);
  }
  if (seen.size === 0) return [...QUOTE_FUNCTION_KEYS];
  return QUOTE_FUNCTION_KEYS.filter((k) => seen.has(k));
}

export function pickPreferredEngagementId(
  projects: Array<Record<string, unknown>>,
  similarProjects?: Array<Record<string, unknown>>,
): string | null {
  const candidates = collectSourceCandidates(projects, similarProjects);
  return candidates.find((c) => c.engagementId)?.engagementId ?? null;
}

function engagementFromSimilarHit(hit: Record<string, unknown>): string | null {
  const meta = (hit.metadata as Record<string, unknown>) || {};
  const eid = hit.engagement_id || meta.engagement_id;
  return eid ? String(eid) : null;
}

function resolveEngagementForProject(
  project: Record<string, unknown>,
  similarProjects?: Array<Record<string, unknown>>,
): string | null {
  if (project.engagement_id) return String(project.engagement_id);
  const rowName = String(project.project_name || "");
  if (!rowName) return null;
  const hit = (similarProjects || []).find((s) => {
    const meta = (s.metadata as Record<string, unknown>) || {};
    return String(meta.project_name || s.project_name || "") === rowName;
  });
  return hit ? engagementFromSimilarHit(hit) : null;
}

/**
 * Columns mirror comparison_table.projects (same order / Top-N).
 * Projects without resolvable engagement_id still appear (checkbox disabled).
 */
export function collectSourceCandidates(
  projects: Array<Record<string, unknown>>,
  similarProjects?: Array<Record<string, unknown>>,
  limit = SOURCE_CANDIDATE_LIMIT,
): SourceCandidate[] {
  const out: SourceCandidate[] = [];
  const seenKeys = new Set<string>();

  for (const [index, p] of (projects || []).entries()) {
    if (out.length >= limit) break;
    const name = String(p.project_name || "").trim() || `历史项目 ${index + 1}`;
    const eid = resolveEngagementForProject(p, similarProjects);
    const columnKey = eid || `project:${name}:${index}`;
    if (seenKeys.has(columnKey)) continue;
    seenKeys.add(columnKey);
    const metaHit = eid
      ? (similarProjects || []).find((s) => engagementFromSimilarHit(s) === eid)
      : undefined;
    const meta = (metaHit?.metadata as Record<string, unknown>) || {};
    const vehicle =
      resolveVehicleModel(p) ||
      resolveVehicleModel(meta) ||
      (meta.vehicle_model != null && String(meta.vehicle_model).trim()
        ? String(meta.vehicle_model).trim()
        : null);
    out.push({
      columnKey,
      engagementId: eid,
      projectName: name,
      customer:
        (p.customer != null && String(p.customer).trim()) ||
        (meta.customer != null ? String(meta.customer) : null) ||
        null,
      vehicleModel: vehicle,
      similarityScore:
        typeof p.similarity_score === "number"
          ? p.similarity_score
          : typeof metaHit?.similarity_score === "number"
            ? metaHit.similarity_score
            : null,
    });
  }

  if (out.length === 0) {
    for (const hit of similarProjects || []) {
      if (out.length >= limit) break;
      const eid = engagementFromSimilarHit(hit);
      if (!eid || seenKeys.has(eid)) continue;
      seenKeys.add(eid);
      const meta = (hit.metadata as Record<string, unknown>) || {};
      out.push({
        columnKey: eid,
        engagementId: eid,
        projectName: String(meta.project_name || hit.project_name || eid),
        customer: meta.customer != null ? String(meta.customer) : null,
        vehicleModel: null,
        similarityScore:
          typeof hit.similarity_score === "number" ? hit.similarity_score : null,
      });
    }
  }

  return out;
}

export function defaultFunctionSourceMap(
  inScope: QuoteFunctionKey[],
  preferredEngagementId: string | null,
): FunctionSourceMap {
  const map = emptyFunctionSourceMap();
  if (!preferredEngagementId) return map;
  for (const key of inScope) {
    map[key] = preferredEngagementId;
  }
  return map;
}

/** Apply one engagement (or null) to all in-scope modules. */
export function applyEngagementToInScope(
  current: FunctionSourceMap,
  inScope: QuoteFunctionKey[],
  engagementId: string | null,
): FunctionSourceMap {
  const next = { ...current };
  for (const key of QUOTE_FUNCTION_KEYS) {
    next[key] = inScope.includes(key) ? engagementId : null;
  }
  return next;
}

/** True when every in-scope module is mapped to this engagement. */
export function isColumnFullySelected(
  map: FunctionSourceMap,
  inScope: QuoteFunctionKey[],
  engagementId: string,
): boolean {
  if (inScope.length === 0) return false;
  return inScope.every((key) => map[key] === engagementId);
}

/**
 * Toggle column: if already fully selected → clear those modules;
 * otherwise select this engagement for all in-scope modules.
 */
export function toggleColumnForInScope(
  current: FunctionSourceMap,
  inScope: QuoteFunctionKey[],
  engagementId: string,
): FunctionSourceMap {
  if (isColumnFullySelected(current, inScope, engagementId)) {
    return applyEngagementToInScope(current, inScope, null);
  }
  return applyEngagementToInScope(current, inScope, engagementId);
}

export function coalesceFunctionSourceMap(
  saved: Record<string, unknown> | null | undefined,
  inScope: QuoteFunctionKey[],
  preferredEngagementId: string | null,
): FunctionSourceMap {
  if (saved && typeof saved === "object") {
    const map = emptyFunctionSourceMap();
    for (const key of QUOTE_FUNCTION_KEYS) {
      const v = saved[key];
      map[key] = v == null || v === "" ? null : String(v);
    }
    return map;
  }
  return defaultFunctionSourceMap(inScope, preferredEngagementId);
}

export function countMappedInScope(
  map: FunctionSourceMap,
  inScope: QuoteFunctionKey[],
): { mapped: number; total: number } {
  let mapped = 0;
  for (const key of inScope) {
    if (map[key]) mapped += 1;
  }
  return { mapped, total: inScope.length };
}

/** Read-only rows for /quote confirmation (does not mutate map). */
export type FunctionSourceSummaryRow = {
  key: QuoteFunctionKey;
  moduleLabel: string;
  inScope: boolean;
  sourceLabel: string;
  engagementId: string | null;
};

export function buildFunctionSourceSummaryRows(
  map: FunctionSourceMap | Record<string, string | null> | null | undefined,
  inScope: QuoteFunctionKey[],
  candidates: SourceCandidate[],
): FunctionSourceSummaryRow[] {
  const nameById = new Map(
    candidates
      .filter((c) => c.engagementId)
      .map((c) => [c.engagementId as string, c.projectName] as const),
  );
  const inScopeSet = new Set(inScope);
  const normalized = coalesceFunctionSourceMap(map ?? null, inScope, null);

  return QUOTE_FUNCTION_KEYS.map((key) => {
    const eid = normalized[key];
    let sourceLabel = "不引用历史";
    if (!inScopeSet.has(key)) {
      sourceLabel = "不在范围";
    } else if (eid) {
      sourceLabel = nameById.get(eid) || eid;
    }
    return {
      key,
      moduleLabel: QUOTE_FUNCTION_SHORT[key],
      inScope: inScopeSet.has(key),
      sourceLabel,
      engagementId: inScopeSet.has(key) ? eid : null,
    };
  });
}

export function formatSimilarityPercent(score?: number | null): string | null {
  if (score == null || Number.isNaN(score)) return null;
  const pct = score <= 1 ? Math.round(score * 100) : Math.round(score);
  return `${pct}%`;
}

export function truncateProjectLabel(name: string, max = 14): string {
  const t = name.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max)}…`;
}
