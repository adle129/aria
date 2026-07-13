/** Canonical engineering-function display: 中文 (Code). */

const FUNCTION_LABELS: Record<string, string> = {
  PM: "项目管理",
  Chassis: "底盘",
  BIW: "车身",
  CAE: "仿真",
  EE: "电子电器",
  GI: "总布置",
  Interior: "内外饰",
  "Test validation": "试验验证",
  Closure: "开闭件",
  Simulation: "仿真",
  PS: "动力系统",
};

/** e.g. BIW → 车身 (BIW); unknown → 待确认 */
export function formatFunctionLabel(code?: string | null): string {
  const key = String(code || "").trim();
  if (!key || key === "未知" || key === "待确认") return "待确认";
  const zh = FUNCTION_LABELS[key];
  if (!zh) return key;
  return `${zh} (${key})`;
}

export function functionLabelMap(): Record<string, string> {
  return { ...FUNCTION_LABELS };
}
