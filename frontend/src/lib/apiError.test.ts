import { describe, expect, it } from "vitest";
import { shouldShowApiError } from "@/api/client";

describe("shouldShowApiError", () => {
  it("suppresses automatic task-not-found restore", () => {
    expect(
      shouldShowApiError(404, "任务 ID 不存在", {
        url: "/rfq/tasks/00000000-0000-0000-0000-000000000000",
      }),
    ).toBe(false);
  });

  it("shows task-not-found for manual load", () => {
    expect(
      shouldShowApiError(404, "任务 ID 不存在", {
        url: "/rfq/tasks/00000000-0000-0000-0000-000000000000",
        showError: true,
      }),
    ).toBe(true);
  });

  it("suppresses when silentError is set", () => {
    expect(
      shouldShowApiError(500, "服务器错误", {
        url: "/rfq/tasks/x",
        silentError: true,
      }),
    ).toBe(false);
  });

  it("shows other endpoint 404", () => {
    expect(
      shouldShowApiError(404, "基准维度库不存在", {
        url: "/rfq/dimension-baseline",
      }),
    ).toBe(true);
  });
});
