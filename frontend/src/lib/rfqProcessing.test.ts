import { describe, expect, it } from "vitest";
import {
  formatQueueWaitHint,
  isQueueWaiting,
  resolveProcessingStepIndex,
  resolveProcessingStepVisuals,
} from "@/components/rfq/RfqAnalysisProgress";

describe("resolveProcessingStepIndex", () => {
  it("maps queued to parse step (upload already done)", () => {
    expect(resolveProcessingStepIndex("queued", 0)).toBe(1);
  });

  it("maps parsing below 35% to parse step", () => {
    expect(resolveProcessingStepIndex("parsing", 20)).toBe(1);
  });

  it("maps parsing at 40% to dimension step", () => {
    expect(resolveProcessingStepIndex("parsing", 40)).toBe(2);
  });

  it("maps dimension_review to review step", () => {
    expect(resolveProcessingStepIndex("dimension_review", 40)).toBe(3);
  });
});

describe("isQueueWaiting", () => {
  it("is true when queued even without position", () => {
    expect(isQueueWaiting("queued", null)).toBe(true);
  });

  it("is false when parsing even with stale queue position", () => {
    expect(isQueueWaiting("parsing", 1)).toBe(false);
  });
});

describe("formatQueueWaitHint", () => {
  it("includes position and ETA minutes", () => {
    expect(
      formatQueueWaitHint({
        processingStatus: "queued",
        queuePosition: 2,
        estimatedWaitSeconds: 90,
      }),
    ).toBe("排队中：第 2 位 · 预计约 2 分钟");
  });

  it("says ETA unavailable when wait seconds missing", () => {
    expect(
      formatQueueWaitHint({
        processingStatus: "pending",
        queuePosition: null,
        estimatedWaitSeconds: null,
      }),
    ).toContain("预计等待时间暂不可用");
  });
});

describe("resolveProcessingStepVisuals", () => {
  it("shows upload done and queue wait when another job is ahead", () => {
    const steps = resolveProcessingStepVisuals("queued", 0, 1);
    expect(steps[0]).toEqual({ label: "文件上传", state: "done" });
    expect(steps[1]).toEqual({ label: "排队等待", state: "active" });
    expect(steps[2].state).toBe("pending");
  });

  it("shows queue wait when queued without explicit position", () => {
    const steps = resolveProcessingStepVisuals("queued", 0, null);
    expect(steps[0].state).toBe("done");
    expect(steps[1]).toEqual({ label: "排队等待", state: "active" });
  });

  it("shows retrieve step after engineer confirmation", () => {
    const steps = resolveProcessingStepVisuals("retrieving", 55, null);
    expect(steps.slice(0, 4).every((step) => step.state === "done")).toBe(true);
    expect(steps[4]).toEqual({
      label: "检索相似历史项目",
      state: "active",
    });
  });
});
