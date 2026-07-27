import { describe, expect, it } from "vitest";
import { formatHardRefDeleteTip } from "./hardRefDeleteTip";

describe("formatHardRefDeleteTip", () => {
  it("falls back when no task ids", () => {
    expect(formatHardRefDeleteTip([])).toBe(
      "有报价任务在使用本项目，无法删除",
    );
  });

  it("lists up to three task ids", () => {
    expect(formatHardRefDeleteTip(["a", "b"])).toBe(
      "有报价任务在使用本项目，无法删除（任务：a、b）",
    );
  });

  it("summarizes when more than three", () => {
    expect(formatHardRefDeleteTip(["t1", "t2", "t3", "t4"])).toBe(
      "有报价任务在使用本项目，无法删除（任务：t1、t2、t3 等 4 个任务）",
    );
  });
});
