import { describe, expect, it } from "vitest";
import { masterDataSelectOptions } from "./masterData";

describe("masterDataSelectOptions", () => {
  it("lists active names for pickers", () => {
    expect(
      masterDataSelectOptions([
        { id: "1", name: "OEM-A", is_active: true },
        { id: "2", name: "OEM-B", is_active: false },
      ]),
    ).toEqual([{ value: "OEM-A", label: "OEM-A", disabled: false }]);
  });
});
