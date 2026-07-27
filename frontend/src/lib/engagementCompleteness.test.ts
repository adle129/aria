import { describe, expect, it } from "vitest";
import {
  formatEngagementIndexStatus,
  formatEngagementTier,
} from "./engagementCompleteness";

describe("formatEngagementTier", () => {
  it("maps tiers to customer-facing Chinese labels", () => {
    expect(formatEngagementTier("gold").label).toBe("金级");
    expect(formatEngagementTier("silver").label).toBe("银级");
    expect(formatEngagementTier("copper").label).toBe("铜级");
  });

  it("shows pending evaluation hint when tier is missing", () => {
    expect(formatEngagementTier(null).label).toBe("待评估");
    expect(formatEngagementTier(undefined).tip).toMatch(/更新知识库索引/);
  });
});

describe("formatEngagementIndexStatus", () => {
  it("maps index statuses to Chinese labels", () => {
    expect(formatEngagementIndexStatus("indexed").label).toBe("可检索");
    expect(formatEngagementIndexStatus("pending").label).toBe("待更新");
    expect(formatEngagementIndexStatus("failed").label).toBe("更新失败");
    expect(formatEngagementIndexStatus("failed", { lastError: "缺 RFQ" }).tip).toMatch(
      /缺 RFQ/,
    );
  });
});
