/** Tooltip / message when delete is blocked by RFQ hard references. */
export function formatHardRefDeleteTip(taskIds: string[]): string {
  const ids = taskIds.map((id) => id.trim()).filter(Boolean);
  if (ids.length === 0) {
    return "有报价任务在使用本项目，无法删除";
  }
  const shown = ids.slice(0, 3);
  const extra = ids.length - shown.length;
  const list = shown.join("、");
  const suffix = extra > 0 ? ` 等 ${ids.length} 个任务` : "";
  return `有报价任务在使用本项目，无法删除（任务：${list}${suffix}）`;
}
