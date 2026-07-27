import { describe, expect, it } from "vitest";
import {
  buildMatrixProjectHeaders,
  formatMatrixHeaderTooltip,
  resolveVehicleModel,
  truncateHeaderText,
} from "./matrixProjectHeader";

describe("resolveVehicleModel", () => {
  it("reads 平台类型 from dimensions.value", () => {
    expect(
      resolveVehicleModel({
        dimensions: { 平台类型: { value: "MEB", match: true } },
      }),
    ).toBe("MEB");
  });

  it("reads 车型 string dimension", () => {
    expect(resolveVehicleModel({ dimensions: { 车型: "AU403" } })).toBe("AU403");
  });

  it("falls back to top-level platform_type", () => {
    expect(resolveVehicleModel({ platform_type: "PPE" })).toBe("PPE");
  });

  it("returns null when missing", () => {
    expect(resolveVehicleModel({ project_name: "X" })).toBeNull();
  });
});

describe("buildMatrixProjectHeaders", () => {
  it("fills customer and vehicle or em dash", () => {
    const headers = buildMatrixProjectHeaders([
      {
        project_name: "Proj A",
        customer: "Audi",
        dimensions: { 平台类型: { value: "MEB" } },
      },
      { project_name: "Proj B" },
    ]);
    expect(headers[0]).toEqual({
      project_name: "Proj A",
      customer: "Audi",
      vehicle_model: "MEB",
      engagement_id: null,
    });
    expect(headers[1]).toEqual({
      project_name: "Proj B",
      customer: "—",
      vehicle_model: "—",
      engagement_id: null,
    });
  });
});

describe("formatMatrixHeaderTooltip / truncate", () => {
  it("joins three fields and optional project id", () => {
    expect(
      formatMatrixHeaderTooltip({
        project_name: "P",
        customer: "C",
        vehicle_model: "V",
      }),
    ).toBe("P · C · V");
    expect(
      formatMatrixHeaderTooltip({
        project_name: "P",
        customer: "C",
        vehicle_model: "V",
        engagement_id: "test",
      }),
    ).toBe("P · C · V\n项目编号 test");
  });

  it("truncates long names", () => {
    expect(truncateHeaderText("abcdefghijklmnopqrs", 10)).toBe("abcdefghij…");
  });
});
