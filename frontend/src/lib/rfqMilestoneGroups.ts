/** Normalize RFQ milestone maps for parse-summary UI (customer-facing groups). */

export type MilestoneKind = "acceptance" | "data" | "other";

export interface MilestoneEntry {
  key: string;
  date: string;
  kind: MilestoneKind;
}

export interface MilestoneGroupView {
  kind: MilestoneKind;
  title: string;
  tip: string;
  entries: MilestoneEntry[];
}

const GROUP_META: Record<
  MilestoneKind,
  { title: string; tip: string; order: number }
> = {
  acceptance: {
    title: "验收节点",
    tip: "合同约定的阶段验收时间（如 P2 / P3 / P5），用于对齐交付与付款节奏。",
    order: 0,
  },
  data: {
    title: "数据节点",
    tip: "数模 / 数据发放计划节点（如 M0、EM1、M1），用于评估开发进度与人力峰值。",
    order: 1,
  },
  other: {
    title: "其他时间点",
    tip: "项目启动、SOP 等未归入验收或数据表的时间点。",
    order: 2,
  },
};

const KEY_ORDER = [
  "P1",
  "M0",
  "EM1",
  "M1",
  "EM2",
  "M2",
  "P2",
  "EM3",
  "M3",
  "P3",
  "M4",
  "P4",
  "M5",
  "P5",
  "SOP",
];

function defaultKind(key: string): MilestoneKind {
  const k = key.toUpperCase();
  if (k === "M0" || /^EM[1-3]$/.test(k) || /^M[1-5]$/.test(k)) return "data";
  if (/^P[2-5]$/.test(k)) return "acceptance";
  return "other";
}

function sortEntries(entries: MilestoneEntry[]): MilestoneEntry[] {
  return [...entries].sort((a, b) => {
    const ai = KEY_ORDER.indexOf(a.key.toUpperCase());
    const bi = KEY_ORDER.indexOf(b.key.toUpperCase());
    if (ai >= 0 && bi >= 0) return ai - bi;
    if (ai >= 0) return -1;
    if (bi >= 0) return 1;
    return a.date.localeCompare(b.date) || a.key.localeCompare(b.key);
  });
}

export function buildMilestoneGroupViews(
  milestones: Record<string, string> | null | undefined,
  milestoneGroups?: {
    acceptance?: Record<string, string>;
    data?: Record<string, string>;
    other?: Record<string, string>;
  } | null,
): MilestoneGroupView[] {
  const byKind: Record<MilestoneKind, MilestoneEntry[]> = {
    acceptance: [],
    data: [],
    other: [],
  };

  const grouped =
    milestoneGroups &&
    (milestoneGroups.acceptance || milestoneGroups.data || milestoneGroups.other)
      ? milestoneGroups
      : null;

  if (grouped) {
    (["acceptance", "data", "other"] as MilestoneKind[]).forEach((kind) => {
      const bucket = grouped[kind] || {};
      Object.entries(bucket).forEach(([key, date]) => {
        if (!date) return;
        byKind[kind].push({ key, date: String(date), kind });
      });
    });
  } else {
    Object.entries(milestones || {}).forEach(([key, date]) => {
      if (!date) return;
      const kind = defaultKind(key);
      byKind[kind].push({ key, date: String(date), kind });
    });
  }

  return (["acceptance", "data", "other"] as MilestoneKind[])
    .map((kind) => {
      const meta = GROUP_META[kind];
      return {
        kind,
        title: meta.title,
        tip: meta.tip,
        entries: sortEntries(byKind[kind]),
      };
    })
    .filter((group) => group.entries.length > 0)
    .sort((a, b) => GROUP_META[a.kind].order - GROUP_META[b.kind].order);
}
