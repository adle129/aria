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

  it("maps phase1 cancelling at match progress to match step not review", () => {
    expect(resolveProcessingStepIndex("cancelling", 40)).toBe(2);
    expect(resolveProcessingStepIndex("cancelling", 20)).toBe(1);
  });

  it("maps phase2 cancelling to review step", () => {
    expect(resolveProcessingStepIndex("cancelling", 55)).toBe(3);
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
    ).toBe("排队中：第 2 位 · 预计还需约 2 分钟");
  });

  it("says ETA unavailable when wait seconds missing", () => {
    expect(
      formatQueueWaitHint({
        processingStatus: "pending",
        queuePosition: null,
        estimatedWaitSeconds: null,
      }),
    ).toContain("预计剩余等待时间暂不可用");
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

  it("phase1 cancelling does not mark engineer review done", () => {
    const steps = resolveProcessingStepVisuals("cancelling", 40, null);
    expect(steps[0].state).toBe("done");
    expect(steps[1]).toEqual({ label: "解析 RFQ 文档", state: "done" });
    expect(steps[2]).toEqual({ label: "匹配基准维度库", state: "done" });
    expect(steps[3]).toEqual({ label: "等待工程师确认", state: "pending" });
    expect(steps[4]).toEqual({ label: "正在取消", state: "active" });
  });

  it("phase1 cancelling during early parse keeps match pending", () => {
    const steps = resolveProcessingStepVisuals("cancelling", 20, null);
    expect(steps[1].state).toBe("done");
    expect(steps[2].state).toBe("pending");
    expect(steps[3].state).toBe("pending");
    expect(steps[4]).toEqual({ label: "正在取消", state: "active" });
  });

  it("phase2 cancelling keeps review done", () => {
    const steps = resolveProcessingStepVisuals("cancelling", 55, null);
    expect(steps[3]).toEqual({ label: "等待工程师确认", state: "done" });
    expect(steps[4]).toEqual({ label: "正在取消", state: "active" });
  });
});
