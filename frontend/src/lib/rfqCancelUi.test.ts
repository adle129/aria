import { describe, expect, it } from "vitest";
import { isCancellingUi, shouldApplyStatusToDisplayedTask } from "@/lib/rfqCancelUi";

describe("isCancellingUi", () => {
  it("is true only for the task that requested cancel", () => {
    expect(
      isCancellingUi({
        cancellingTaskId: "task-a",
        displayedTaskId: "task-a",
        processingStatus: "queued",
      }),
    ).toBe(true);
  });

  it("does not leak cancel UI to another queued task", () => {
    expect(
      isCancellingUi({
        cancellingTaskId: "task-a",
        displayedTaskId: "task-b",
        processingStatus: "queued",
      }),
    ).toBe(false);
  });

  it("follows server cancelling status for the displayed task", () => {
    expect(
      isCancellingUi({
        cancellingTaskId: null,
        displayedTaskId: "task-b",
        processingStatus: "cancelling",
      }),
    ).toBe(true);
  });

  it("is false when nothing is cancelling", () => {
    expect(
      isCancellingUi({
        cancellingTaskId: null,
        displayedTaskId: "task-b",
        processingStatus: "queued",
      }),
    ).toBe(false);
  });
});

describe("shouldApplyStatusToDisplayedTask", () => {
  it("accepts status updates for the currently displayed task", () => {
    expect(shouldApplyStatusToDisplayedTask("task-b", "task-b")).toBe(true);
  });

  it("rejects status updates from a background cancelled task", () => {
    expect(shouldApplyStatusToDisplayedTask("task-b", "task-a")).toBe(false);
  });

  it("rejects updates when no task is displayed", () => {
    expect(shouldApplyStatusToDisplayedTask(null, "task-a")).toBe(false);
  });
});
