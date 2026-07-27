import { describe, expect, it } from "vitest";
import { inferDocTypeFromFilename } from "./inferDocType";

describe("inferDocTypeFromFilename", () => {
  it("classifies RFQ / QA / quote by name", () => {
    expect(inferDocTypeFromFilename("RFQ_客户A.docx")).toBe("rfq");
    expect(inferDocTypeFromFilename("Q_A_模板.xlsx")).toBe("qa");
    expect(inferDocTypeFromFilename("报价人力模板.xlsx")).toBe("quote_manpower");
    expect(inferDocTypeFromFilename("方案.pdf")).toBe("summary");
  });

  it("returns null when ambiguous", () => {
    expect(inferDocTypeFromFilename("notes.xlsx")).toBeNull();
    expect(inferDocTypeFromFilename("plain.docx")).toBeNull();
  });
});
