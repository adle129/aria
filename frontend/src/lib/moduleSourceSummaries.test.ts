import { describe, expect, it } from "vitest";
import {
  getModuleSummaryBullets,
  getModuleSummaryStatus,
} from "./moduleSourceSummaries";

describe("moduleSourceSummaries", () => {
  const sample = {
    mode: "placeholder",
    by_engagement: {
      "eng-a": {
        Chassis: {
          bullets: ["底盘悬架（占位）", "制动（占位）"],
          status: "placeholder",
        },
      },
    },
  };

  it("reads bullets for engagement × function", () => {
    expect(getModuleSummaryBullets(sample, "eng-a", "Chassis")).toEqual([
      "底盘悬架（占位）",
      "制动（占位）",
    ]);
    expect(getModuleSummaryBullets(sample, "eng-a", "PM")).toEqual([]);
  });

  it("reads status", () => {
    expect(getModuleSummaryStatus(sample, "eng-a", "Chassis")).toBe("placeholder");
    expect(getModuleSummaryStatus(sample, "missing", "Chassis")).toBeNull();
  });
});
