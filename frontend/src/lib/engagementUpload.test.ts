import { describe, expect, it } from "vitest";
import { uploadNeedsEngagementId } from "./engagementUpload";

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
