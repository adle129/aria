import { describe, expect, it } from "vitest";
import { parseApiTimestamp } from "@/lib/apiTime";
import { formatRelativeTime } from "@/lib/taskStatus";

describe("parseApiTimestamp", () => {
  it("parses Z-suffixed UTC", () => {
    expect(parseApiTimestamp("2026-07-09T06:00:22Z")).toBe(Date.parse("2026-07-09T06:00:22Z"));
  });

  it("treats naive timestamps as UTC", () => {
    expect(parseApiTimestamp("2026-07-09T06:00:22.181814")).toBe(
      Date.parse("2026-07-09T06:00:22.181814Z"),
    );
  });
});

describe("formatRelativeTime UTC fix", () => {
  it("shows minutes not hours for recent naive UTC timestamps", () => {
    const now = Date.parse("2026-07-09T06:10:00Z");
    expect(formatRelativeTime("2026-07-09T06:00:22.181814", now)).toMatch(/^\d+ 分钟前$/);
  });
});
