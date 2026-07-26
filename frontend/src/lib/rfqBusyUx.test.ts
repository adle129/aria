import { describe, expect, it } from "vitest";
import {
  actionAreaErrorFromAxios,
  formatQueueFullActionMessage,
  RFQ_BUSY_ETA_SECONDS_THRESHOLD,
  RFQ_BUSY_HOURS_BANNER_MESSAGE,
  RFQ_BUSY_QUEUE_POSITION_THRESHOLD,
  RFQ_SEARCH_BUSY_503_MESSAGE,
  RFQ_TASK_MAX_QUEUE_SIZE_DEFAULT,
  resolveActionAreaError,
  shouldShowBusyHoursBanner,
} from "@/lib/rfqBusyUx";

describe("shouldShowBusyHoursBanner", () => {
  it("is false when queue and ETA are low", () => {
    expect(
      shouldShowBusyHoursBanner({ queuePosition: 2, estimatedWaitSeconds: 120 }),
    ).toBe(false);
  });

  it("is true when queue position reaches threshold", () => {
    expect(
      shouldShowBusyHoursBanner({
        queuePosition: RFQ_BUSY_QUEUE_POSITION_THRESHOLD,
        estimatedWaitSeconds: 30,
      }),
    ).toBe(true);
  });

  it("is true when ETA reaches threshold", () => {
    expect(
      shouldShowBusyHoursBanner({
        queuePosition: 1,
        estimatedWaitSeconds: RFQ_BUSY_ETA_SECONDS_THRESHOLD,
      }),
    ).toBe(true);
  });

  it("handles nulls", () => {
    expect(shouldShowBusyHoursBanner({})).toBe(false);
    expect(shouldShowBusyHoursBanner({ queuePosition: null })).toBe(false);
  });
});

describe("formatQueueFullActionMessage", () => {
  it("includes depth and default max", () => {
    expect(formatQueueFullActionMessage({ queueDepth: 20 })).toContain(
      `20/${RFQ_TASK_MAX_QUEUE_SIZE_DEFAULT}`,
    );
    expect(formatQueueFullActionMessage({ queueDepth: 20 })).toContain("请稍后再上传");
  });

  it("allows custom max", () => {
    expect(formatQueueFullActionMessage({ queueDepth: 5, maxQueueSize: 5 })).toContain(
      "5/5",
    );
  });
});

describe("resolveActionAreaError", () => {
  it("maps 429 to queue-full copy", () => {
    const err = resolveActionAreaError({ httpStatus: 429, queueDepth: 20 });
    expect(err?.kind).toBe("queue_full");
    expect(err?.message).toContain("排队人数已满");
  });

  it("maps 503 to search-busy copy", () => {
    const err = resolveActionAreaError({ httpStatus: 503 });
    expect(err?.kind).toBe("search_busy");
    expect(err?.message).toBe(RFQ_SEARCH_BUSY_503_MESSAGE);
  });
});

describe("actionAreaErrorFromAxios", () => {
  it("reads queue_depth from 429 body", () => {
    const err = actionAreaErrorFromAxios({
      response: { status: 429, data: { msg: "full", queue_depth: 18 } },
    });
    expect(err?.message).toContain("18/");
  });
});

describe("banner copy", () => {
  it("matches plan §5.4 wording", () => {
    expect(RFQ_BUSY_HOURS_BANNER_MESSAGE).toContain("使用的人较多");
    expect(RFQ_BUSY_HOURS_BANNER_MESSAGE).toContain("错开高峰");
  });
});
