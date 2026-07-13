import { describe, expect, it } from "vitest";
import { formatFunctionLabel } from "./functionLabels";

describe("formatFunctionLabel", () => {
  it("renders Chinese with English code", () => {
    expect(formatFunctionLabel("BIW")).toBe("车身 (BIW)");
    expect(formatFunctionLabel("Chassis")).toBe("底盘 (Chassis)");
    expect(formatFunctionLabel("GI")).toBe("总布置 (GI)");
  });

  it("keeps bilingual form and maps unknown", () => {
    expect(formatFunctionLabel("CAE")).toBe("仿真 (CAE)");
    expect(formatFunctionLabel("未知")).toBe("待确认");
    expect(formatFunctionLabel("")).toBe("待确认");
  });
});
