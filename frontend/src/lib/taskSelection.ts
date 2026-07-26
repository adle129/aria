import { LAST_TASK_ID_KEY } from "@/api/client";

export const TASK_CHANGED_EVENT = "aria-task-changed";

/** Persist last task id without broadcasting (local sync / upload already bound UI). */
export function rememberLastTaskId(taskId: string) {
  if (typeof window === "undefined") return;
  const id = taskId.trim();
  if (!id) return;
  sessionStorage.setItem(LAST_TASK_ID_KEY, id);
}

/**
 * Persist + broadcast selection change (sidebar open, cross-page jump).
 * Callers that already bind the displayed task must use rememberLastTaskId only.
 */
export function notifyTaskChanged(taskId: string) {
  const id = taskId.trim();
  if (!id || typeof window === "undefined") return;
  rememberLastTaskId(id);
  window.dispatchEvent(new CustomEvent(TASK_CHANGED_EVENT, { detail: id }));
}
