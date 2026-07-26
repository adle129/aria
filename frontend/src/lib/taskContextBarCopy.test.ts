import { describe, expect, it } from "vitest";
import {
  contextBarOpenLabel,
  formatContextBarHeadline,
  formatContextBarQueueHint,
  formatContextBarTagLabel,
  shouldPollContextBarStatus,
} from "@/lib/taskContextBarCopy";

describe("formatContextBarTagLabel", () => {
  it("marks dimension_review as human action", () => {
    expect(formatContextBarTagLabel("dimension_review")).toBe("待您确认");
  });

  it("marks machine states briefly", () => {
    expect(formatContextBarTagLabel("queued")).toBe("排队中");
    expect(formatContextBarTagLabel("parsing")).toBe("解析中");
  });
});

describe("formatContextBarHeadline", () => {
  it("includes queue position when present", () => {
    expect(
      formatContextBarHeadline({
        fileName: "RFQ_A.doc",
        processingStatus: "queued",
        queuePosition: 2,
      }),
    ).toBe("RFQ_A.doc 正在排队（第 2 位）");
  });

  it("uses review wording for dimension_review", () => {
    expect(
      formatContextBarHeadline({
        fileName: "RFQ_A.doc",
        processingStatus: "dimension_review",
      }),
    ).toContain("待您确认");
  });

  it("describes parsing without queue suffix", () => {
    expect(
      formatContextBarHeadline({
        fileName: "RFQ_A.doc",
        processingStatus: "parsing",
        queuePosition: 1,
      }),
    ).toBe("RFQ_A.doc 正在解析");
  });
});

describe("formatContextBarQueueHint", () => {
  it("returns null when not queued", () => {
    expect(
      formatContextBarQueueHint({ processingStatus: "parsing", queuePosition: 1 }),
    ).toBeNull();
  });

  it("formats position and ETA", () => {
    expect(
      formatContextBarQueueHint({
        processingStatus: "queued",
        queuePosition: 3,
        estimatedWaitSeconds: 600,
      }),
    ).toContain("第 3 位");
  });
});

describe("shouldPollContextBarStatus", () => {
  it("polls machine-running only", () => {
    expect(shouldPollContextBarStatus("queued")).toBe(true);
    expect(shouldPollContextBarStatus("dimension_review")).toBe(false);
  });
});

describe("contextBarOpenLabel", () => {
  it("uses confirm CTA for review", () => {
    expect(contextBarOpenLabel("dimension_review")).toBe("前往确认维度");
  });

  it("uses progress CTA while machine is running", () => {
    expect(contextBarOpenLabel("queued")).toBe("查看进度");
    expect(contextBarOpenLabel("parsing")).toBe("查看进度");
  });

  it("uses generic open label when idle/complete", () => {
    expect(contextBarOpenLabel("completed")).toBe("在 RFQ 分析中打开");
  });
});
