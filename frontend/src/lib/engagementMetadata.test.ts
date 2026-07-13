import { describe, expect, it } from "vitest";
import {
  engagementYearOptions,
  formatEngagementMetadataSummary,
  isEngagementMetadataComplete,
} from "./engagementMetadata";

describe("engagementMetadata", () => {
  it("marks incomplete when business fields missing", () => {
    expect(
      isEngagementMetadataComplete({
        project_name: "Demo",
        customer: null,
        year: null,
        functions: [],
      }),
    ).toBe(false);
  });

  it("marks complete when all required fields present", () => {
    expect(
      isEngagementMetadataComplete({
        project_name: "Demo",
        customer: "OEM",
        year: 2024,
        functions: ["Chassis"],
      }),
    ).toBe(true);
  });

  it("formats summary", () => {
    expect(
      formatEngagementMetadataSummary({
        customer: "OEM",
        year: 2024,
        functions: ["PM", "Chassis"],
      }),
    ).toBe("OEM · 2024 · PM / Chassis");
    expect(formatEngagementMetadataSummary({})).toBe("—");
  });

  it("builds descending year options around current year", () => {
    const options = engagementYearOptions(new Date("2026-07-13T00:00:00Z"));
    expect(options[0]).toEqual({ value: 2027, label: "2027" });
    expect(options[1]).toEqual({ value: 2026, label: "2026" });
    expect(options.at(-1)).toEqual({ value: 2006, label: "2006" });
    expect(options).toHaveLength(22);
  });
});
