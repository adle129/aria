/** Whether the RFQ progress panel should show cancel UI for the displayed task. */
export function isCancellingUi(options: {
  cancellingTaskId: string | null;
  displayedTaskId: string | null | undefined;
  processingStatus?: string | null;
}): boolean {
  const { cancellingTaskId, displayedTaskId, processingStatus } = options;
  if (processingStatus === "cancelling") return true;
  return cancellingTaskId != null && cancellingTaskId === displayedTaskId;
}

/** Ignore poll/cancel status writes when the user has switched to another task. */
export function shouldApplyStatusToDisplayedTask(
  displayedTaskId: string | null | undefined,
  sourceTaskId: string,
): boolean {
  return displayedTaskId != null && displayedTaskId === sourceTaskId;
}
