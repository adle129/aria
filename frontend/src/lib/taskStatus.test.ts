import { describe, expect, it } from "vitest";
import {
  formatProcessingStatus,
  formatRecentTaskLabel,
  formatRelativeTime,
  formatTaskListStatus,
  getProcessingStatusTagColor,
  getProcessingStatusTagStyle,
} from "@/lib/taskStatus";

describe("formatProcessingStatus", () => {
  it("maps known statuses to Chinese", () => {
    expect(formatProcessingStatus("queued")).toBe("排队等待中");
    expect(formatProcessingStatus("parsing")).toBe("解析中");
  });

  it("falls back to raw status", () => {
    expect(formatProcessingStatus("unknown")).toBe("unknown");
  });
});

describe("getProcessingStatusTagColor", () => {
  it("maps statuses to tag colors", () => {
    expect(getProcessingStatusTagColor("parsing")).toBe("processing");
    expect(getProcessingStatusTagColor("dimension_review")).toBe("warning");
    expect(getProcessingStatusTagColor("completed")).toBe("success");
    expect(getProcessingStatusTagColor("failed")).toBe("error");
  });
});

describe("getProcessingStatusTagStyle", () => {
  it("returns soft palette for known statuses", () => {
    const style = getProcessingStatusTagStyle("dimension_review");
    expect(style.color).toBe("#A67C2D");
    expect(style.background).toBe("#FBF6EB");
  });
});

describe("formatRelativeTime", () => {
  it("formats recent times as relative", () => {
    const now = Date.parse("2026-07-09T10:00:00Z");
    expect(formatRelativeTime("2026-07-09T09:58:00Z", now)).toBe("2 分钟前");
    expect(formatRelativeTime("2026-07-09T08:00:00Z", now)).toBe("2 小时前");
  });

  it("falls back for missing", () => {
    expect(formatRelativeTime(undefined)).toBe("—");
  });
});

describe("formatTaskListStatus", () => {
  it("prefers status_message while task is in flight", () => {
    expect(
      formatTaskListStatus({
        processing_status: "parsing",
        status_message: "正在匹配基准维度库（1/3）...",
      }),
    ).toBe("正在匹配基准维度库（1/3）");
  });

  it("uses localized status when idle", () => {
    expect(
      formatTaskListStatus({
        processing_status: "dimension_review",
        status_message: "等待工程师确认基准维度清单",
      }),
    ).toBe("等待基准维度勾选");
  });
});

describe("formatRecentTaskLabel", () => {
  it("includes localized status", () => {
    const label = formatRecentTaskLabel({
      task_id: "6276ca76-0000-0000-0000-000000000000",
      file_name: "RFQ_模板.doc",
      processing_status: "parsing",
      created_at: "2026-07-09T02:00:00Z",
    });
    expect(label).toContain("RFQ_模板.doc");
    expect(label).toContain("解析中");
    expect(label).toContain("6276ca76");
  });
});
