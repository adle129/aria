import { describe, expect, it } from "vitest";
import { buildMilestoneGroupViews } from "./rfqMilestoneGroups";

describe("buildMilestoneGroupViews", () => {
  it("splits acceptance vs data from milestone_groups", () => {
    const views = buildMilestoneGroupViews(
      {
        P2: "2022-06-30",
        P3: "2022-10-15",
        P5: "2023-05-30",
        M0: "2022-02-25",
        EM1: "2022-03-25",
        M1: "2022-04-30",
      },
      {
        acceptance: { P2: "2022-06-30", P3: "2022-10-15", P5: "2023-05-30" },
        data: { M0: "2022-02-25", EM1: "2022-03-25", M1: "2022-04-30" },
        other: {},
      },
    );
    expect(views.map((v) => v.kind)).toEqual(["acceptance", "data"]);
    expect(views[0].title).toBe("验收节点");
    expect(views[0].entries.map((e) => e.key)).toEqual(["P2", "P3", "P5"]);
    expect(views[1].entries.map((e) => e.key)).toEqual(["M0", "EM1", "M1"]);
  });

  it("falls back to key families when groups missing", () => {
    const views = buildMilestoneGroupViews({
      P2: "2022-06-30",
      M0: "2022-02-25",
      SOP: "2023-08-30",
    });
    expect(views.find((v) => v.kind === "acceptance")?.entries[0].key).toBe("P2");
    expect(views.find((v) => v.kind === "data")?.entries[0].key).toBe("M0");
    expect(views.find((v) => v.kind === "other")?.entries[0].key).toBe("SOP");
  });
});
