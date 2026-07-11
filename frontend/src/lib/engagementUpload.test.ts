import { describe, expect, it } from "vitest";
import {
  MAX_UPLOAD_FILE_BYTES,
  uploadNeedsEngagementId,
  validateEngagementUpload,
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

describe("validateEngagementUpload", () => {
  it("rejects ZIP and loose file mixtures", () => {
    expect(
      validateEngagementUpload([
        { name: "pack.zip", size: 10 },
        { name: "RFQ.docx", size: 10 },
      ]),
    ).toContain("混传");
  });

  it("rejects more than five ZIP packs", () => {
    const files = Array.from({ length: 6 }, (_, index) => ({
      name: `${index}.zip`,
      size: 10,
    }));
    expect(validateEngagementUpload(files)).toContain("5");
  });

  it("rejects files over 100MB", () => {
    expect(
      validateEngagementUpload([
        { name: "large.zip", size: MAX_UPLOAD_FILE_BYTES + 1 },
      ]),
    ).toContain("100MB");
  });

  it("accepts a bounded loose file set", () => {
    expect(
      validateEngagementUpload([
        { name: "RFQ.docx", size: 1024 },
        { name: "Q_A.xlsx", size: 2048 },
      ]),
    ).toBeNull();
  });
});
