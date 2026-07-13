/** Helpers for RFQ parse-summary module table (draft scope, not final WBS). */

import { formatFunctionLabel } from "@/lib/functionLabels";

export type FunctionSource = "keyword" | "parent_section" | "llm" | "unknown" | string;

export interface RfqModuleRow {
  function?: string;
  function_source?: FunctionSource;
  function_inherited_from?: string;
  module_name?: string;
  description?: string;
  deliverables?: string[];
  deliverables_source?: "function_table" | "section_4_2" | "aligned" | "work_item" | string;
  estimated_complexity?: string;
  section_id?: string;
  section_path?: string;
  l2_title?: string;
  l3_title?: string;
  section_kind?: string;
}

export interface DeliverableGroup {
  category: string;
  function?: string;
  items: string[];
}

export interface WorkSectionCategory {
  key: string;
  label: string;
  function?: string | null;
  rows: RfqModuleRow[];
}

export interface WorkSection {
  title: string;
  kind: string;
  categories: WorkSectionCategory[];
}

export interface ModuleQualityStats {
  total: number;
  knownFunction: number;
  unknownFunction: number;
  withDeliverables: number;
  withoutDeliverables: number;
  unassessedComplexity: number;
  lowDeliverableCoverage: boolean;
  manyUnknownFunctions: boolean;
}

export interface ModuleFunctionGroup {
  functionKey: string;
  label: string;
  rows: RfqModuleRow[];
  withDeliverables: number;
}

const UNASSESSED = new Set(["", "未评估", "—", "-", "unknown"]);

export function isUnassessedComplexity(value?: string | null): boolean {
  return UNASSESSED.has(String(value || "").trim());
}

export function isUnknownFunction(value?: string | null): boolean {
  const text = String(value || "").trim();
  return !text || text === "未知";
}

export function computeModuleQualityStats(modules: RfqModuleRow[]): ModuleQualityStats {
  const total = modules.length;
  let knownFunction = 0;
  let unknownFunction = 0;
  let withDeliverables = 0;
  let unassessedComplexity = 0;
  for (const row of modules) {
    if (isUnknownFunction(row.function)) unknownFunction += 1;
    else knownFunction += 1;
    if ((row.deliverables || []).length > 0) withDeliverables += 1;
    if (isUnassessedComplexity(row.estimated_complexity)) unassessedComplexity += 1;
  }
  const withoutDeliverables = total - withDeliverables;
  return {
    total,
    knownFunction,
    unknownFunction,
    withDeliverables,
    withoutDeliverables,
    unassessedComplexity,
    lowDeliverableCoverage: total > 0 && withDeliverables < Math.max(2, Math.floor(total / 4)),
    manyUnknownFunctions: total > 0 && unknownFunction / total >= 0.25,
  };
}

export function groupModulesByFunction(modules: RfqModuleRow[]): ModuleFunctionGroup[] {
  const buckets = new Map<string, RfqModuleRow[]>();
  for (const row of modules) {
    const key = isUnknownFunction(row.function) ? "待确认" : String(row.function);
    const list = buckets.get(key) || [];
    list.push(row);
    buckets.set(key, list);
  }
  const groups: ModuleFunctionGroup[] = [...buckets.entries()].map(([functionKey, rows]) => ({
    functionKey,
    label:
      functionKey === "待确认" ? "待确认（领域未识别）" : formatFunctionLabel(functionKey),
    rows,
    withDeliverables: rows.filter((r) => (r.deliverables || []).length > 0).length,
  }));
  groups.sort((a, b) => {
    if (a.functionKey === "待确认") return 1;
    if (b.functionKey === "待确认") return -1;
    return a.functionKey.localeCompare(b.functionKey);
  });
  return groups;
}

export function sortRowsByFunction(rows: RfqModuleRow[]): RfqModuleRow[] {
  return [...rows].sort((a, b) => {
    const ka = isUnknownFunction(a.function) ? "\uffff" : String(a.function || "");
    const kb = isUnknownFunction(b.function) ? "\uffff" : String(b.function || "");
    if (ka !== kb) return ka.localeCompare(kb);
    const sa = String(a.section_id || a.module_name || "");
    const sb = String(b.section_id || b.module_name || "");
    return sa.localeCompare(sb, undefined, { numeric: true });
  });
}

export function normalizeWorkSections(
  sections: WorkSection[] | undefined | null,
): WorkSection[] {
  if (!Array.isArray(sections)) return [];
  return sections
    .map((s) => ({
      title: String(s.title || "").trim() || "其他",
      kind: String(s.kind || "other"),
      categories: (s.categories || [])
        .map((c) => ({
          key: String(c.key || "待确认"),
          label: String(c.label || c.key || "").trim() || "未分类",
          function: c.function,
          rows: sortRowsByFunction(Array.isArray(c.rows) ? c.rows : []),
        }))
        .filter((c) => c.rows.length > 0),
    }))
    .filter((s) => s.categories.length > 0);
}

/** Prefer backend work_sections; fall back to flat modules grouped by function. */
export function resolveWorkSections(
  sections: WorkSection[] | undefined | null,
  modules: RfqModuleRow[],
): WorkSection[] {
  const normalized = normalizeWorkSections(sections);
  if (normalized.length > 0) return normalized;
  if (!modules.length) return [];
  const groups = groupModulesByFunction(modules);
  return [
    {
      title: "工作内容",
      kind: "work_content",
      categories: groups.map((g) => ({
        key: g.functionKey,
        label: g.label,
        function: g.functionKey === "待确认" ? null : g.functionKey,
        rows: g.rows,
      })),
    },
  ];
}

export function workSectionCategoryLabel(category: WorkSectionCategory): string {
  const label = String(category.label || "").trim();
  if (label) return label;
  if (category.key === "_all") return "";
  if (category.key === "待确认" || isUnknownFunction(category.function)) {
    return "待确认（领域未识别）";
  }
  if (category.function) {
    return formatFunctionLabel(String(category.function));
  }
  return String(category.key || "未分类");
}

export function normalizeDeliverableGroups(
  groups: DeliverableGroup[] | undefined | null,
): DeliverableGroup[] {
  if (!Array.isArray(groups)) return [];
  return groups
    .map((g) => ({
      category: String(g.category || "未分类交付物").trim() || "未分类交付物",
      function: g.function,
  // Keep stage-tagged labels distinct; trim only blanks.
  // Backend appends （P2）/（P3） so same title on different gates stay unique.
  items: (g.items || []).map((x) => String(x).trim()).filter(Boolean),
    }))
    .filter((g) => g.items.length > 0);
}

export function countDeliverableItems(groups: DeliverableGroup[]): number {
  return groups.reduce((sum, g) => sum + g.items.length, 0);
}

export function functionSourceLabel(source?: string | null, inheritedFrom?: string | null): string {
  switch (source) {
    case "keyword":
      return "标题关键词";
    case "parent_section":
      return inheritedFrom ? `继承自 ${inheritedFrom}` : "继承自上级章节";
    case "llm":
      return "模型补全";
    case "unknown":
      return "待确认";
    default:
      return source ? String(source) : "—";
  }
}
