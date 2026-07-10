import { describe, expect, it } from "vitest";
import { MILESTONE_SCAFFOLD } from "./milestoneScaffold";

describe("MILESTONE_SCAFFOLD", () => {
  it("defines M3/M4/M5 content for quote, qa, proposal", () => {
    expect(MILESTONE_SCAFFOLD.quote.milestone).toBe("M3");
    expect(MILESTONE_SCAFFOLD.qa.milestone).toBe("M4");
    expect(MILESTONE_SCAFFOLD.proposal.milestone).toBe("M5");
    expect(MILESTONE_SCAFFOLD.quote.deliverables.length).toBeGreaterThan(0);
  });
});
