import { describe, expect, it } from "vitest";
import {
  formatProjectIdLine,
  matchesProjectKeyword,
  PROJECT_ID_LABEL,
} from "./projectIdentity";

describe("projectIdentity", () => {
  it("formats customer-facing id line", () => {
    expect(formatProjectIdLine("test")).toBe(`${PROJECT_ID_LABEL} test`);
    expect(formatProjectIdLine("orphan:x")).toBeNull();
    expect(formatProjectIdLine("")).toBeNull();
  });

  it("matches keyword against id name customer vehicle", () => {
    const row = {
      engagement_id: "gm-2026-a",
      project_name: "上海通用汽车",
      customer: "上海通用汽车",
      vehicle_model: "新能源纯电",
    };
    expect(matchesProjectKeyword(row, "gm-2026")).toBe(true);
    expect(matchesProjectKeyword(row, "新能源")).toBe(true);
    expect(matchesProjectKeyword(row, "不存在")).toBe(false);
    expect(matchesProjectKeyword(row, "  ")).toBe(true);
  });
});
