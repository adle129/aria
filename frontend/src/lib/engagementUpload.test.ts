import { describe, expect, it } from "vitest";
import {
  engagementTier,
  missingAutomationImpact,
  uploadNeedsEngagementId,
} from "./engagementUpload";

describe("uploadNeedsEngagementId", () => {
  it("returns false for zip-only selection", () => {
    expect(uploadNeedsEngagementId(["pack.zip"])).toBe(false);
  });

  it("returns true for loose files", () => {
    expect(uploadNeedsEngagementId(["RFQ.docx", "Q_A.xlsx"])).toBe(true);
  });

  it("returns false when empty", () => {
    expect(uploadNeedsEngagementId([])).toBe(false);
  });
});

describe("engagementTier", () => {
  it("returns 金级 when complete", () => {
    expect(engagementTier([])).toBe("金级");
  });

  it("returns 银级 when only quote missing", () => {
    expect(engagementTier(["quote_manpower"])).toBe("银级");
  });

  it("returns 铜级 when qa missing", () => {
    expect(engagementTier(["qa"])).toBe("铜级");
  });
});

describe("missingAutomationImpact", () => {
  it("lists M3/M4 impacts", () => {
    expect(missingAutomationImpact(["qa", "quote_manpower"])).toEqual([
      "缺 Q&A：第三期 Q&A 自动生成不可用（M4）",
      "缺人力报价 Excel：第二期报价 Excel 自动生成不可用（M3）",
    ]);
  });
});