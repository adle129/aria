import { describe, expect, it } from "vitest";
import { formatDurationMs, formatTaskTimingLine } from "./formatDuration";

describe("formatDurationMs", () => {
  it("formats seconds and minutes", () => {
    expect(formatDurationMs(0)).toBe("0秒");
    expect(formatDurationMs(45000)).toBe("45秒");
    expect(formatDurationMs(83000)).toBe("1分23秒");
    expect(formatDurationMs(120000)).toBe("2分");
  });

  it("returns null for invalid", () => {
    expect(formatDurationMs(null)).toBeNull();
    expect(formatDurationMs(undefined)).toBeNull();
    expect(formatDurationMs(-1)).toBeNull();
  });
});

describe("formatTaskTimingLine", () => {
  it("builds queue and run line", () => {
    expect(
      formatTaskTimingLine({ queueWaitMs: 5000, runMs: 65000 }),
    ).toBe("排队 5秒 · 解析 1分5秒");
    expect(
      formatTaskTimingLine({ queueWaitMs: 12000, runMs: null, live: true }),
    ).toBe("已等待 12秒");
  });
});
