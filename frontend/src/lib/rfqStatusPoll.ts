/**
 * Per-task RFQ status poll sessions.
 * Starting a poll for task B must not cancel an in-flight poll for task A
 * (global epoch previously caused Phase2 UI to stick until full page refresh).
 */
export class RfqPollSessionMap {
  private epochs = new Map<string, number>();
  private active = new Set<string>();

  begin(taskId: string): number {
    const next = (this.epochs.get(taskId) ?? 0) + 1;
    this.epochs.set(taskId, next);
    this.active.add(taskId);
    return next;
  }

  isCurrent(taskId: string, epoch: number): boolean {
    return this.epochs.get(taskId) === epoch;
  }

  end(taskId: string, epoch: number): void {
    if (this.epochs.get(taskId) === epoch) {
      this.active.delete(taskId);
    }
  }

  /** Stop in-flight polls for one task (e.g. background sync already applied terminal). */
  invalidate(taskId: string): void {
    this.epochs.set(taskId, (this.epochs.get(taskId) ?? 0) + 1);
    this.active.delete(taskId);
  }

  /** Workspace reset / leave page: invalidate every in-flight poll. */
  invalidateAll(): void {
    for (const id of this.epochs.keys()) {
      this.epochs.set(id, (this.epochs.get(id) ?? 0) + 1);
    }
    this.active.clear();
  }

  isActive(taskId: string): boolean {
    return this.active.has(taskId);
  }
}

/** Background status sync should follow the displayed task, never a sibling poll. */
export function resolveStatusWatchTaskId(options: {
  displayedTaskId: string | null | undefined;
  activePollTaskId: string | null | undefined;
}): string | null {
  const displayed = options.displayedTaskId?.trim() || null;
  if (displayed) return displayed;
  const active = options.activePollTaskId?.trim() || null;
  return active;
}

/**
 * Only the displayed task should keep a tight status poll.
 * Sibling uploads must not leave orphaned 500ms loops (request storms + Network Error toasts).
 */
export function shouldContinueStatusPoll(options: {
  displayedTaskId: string | null | undefined;
  pollTaskId: string;
}): boolean {
  const displayed = options.displayedTaskId?.trim() || "";
  const pollId = options.pollTaskId.trim();
  if (!pollId) return false;
  // Allow first ticks before React commits displayedTaskId (upload just bound the task).
  if (!displayed) return true;
  return displayed === pollId;
}
