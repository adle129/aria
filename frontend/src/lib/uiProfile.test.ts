import { describe, expect, it } from "vitest";
import {
  getStepMilestone,
  isFormalDeliveryProfile,
  isPathLockedInR1,
  isQuotingStepDelivered,
  isR1Profile,
  isTaskContextBarVisible,
  resolveUiProfile,
  shouldBlockPath,
  showDemoChrome,
} from "./uiProfile";

describe("resolveUiProfile", () => {
  it("prefers health profile over env default", () => {
    expect(resolveUiProfile("r1")).toBe("r1");
  });

  it("falls back to experience for unknown values", () => {
    expect(resolveUiProfile("unknown")).toBe("experience");
  });
});

describe("r1 route lock", () => {
  it("blocks undelivered quoting steps and debug", () => {
    expect(isPathLockedInR1("/proposal")).toBe(true);
    expect(isPathLockedInR1("/qa")).toBe(true);
    expect(isPathLockedInR1("/quote")).toBe(true);
    expect(isPathLockedInR1("/knowledge/debug")).toBe(true);
    expect(isPathLockedInR1("/rfq")).toBe(false);
    expect(isPathLockedInR1("/knowledge")).toBe(false);
  });

  it("shouldBlockPath only for r1 profile", () => {
    expect(shouldBlockPath("r1", "/proposal")).toBe(true);
    expect(shouldBlockPath("full", "/proposal")).toBe(false);
    expect(shouldBlockPath("experience", "/qa")).toBe(false);
  });
});

describe("isQuotingStepDelivered", () => {
  it("r1 delivers rfq only", () => {
    expect(isQuotingStepDelivered("r1", "rfq")).toBe(true);
    expect(isQuotingStepDelivered("r1", "proposal")).toBe(false);
    expect(isQuotingStepDelivered("r1", "qa")).toBe(false);
    expect(isQuotingStepDelivered("r1", "quote")).toBe(false);
  });

  it("full profile delivers all steps", () => {
    expect(isQuotingStepDelivered("full", "quote")).toBe(true);
  });
});

describe("isTaskContextBarVisible", () => {
  it("hides on knowledge and login", () => {
    expect(isTaskContextBarVisible("/knowledge")).toBe(false);
    expect(isTaskContextBarVisible("/knowledge/debug")).toBe(false);
    expect(isTaskContextBarVisible("/login")).toBe(false);
    expect(isTaskContextBarVisible("/rfq")).toBe(true);
  });
});

describe("showDemoChrome", () => {
  it("only experience and dev show demo UI", () => {
    expect(showDemoChrome("experience")).toBe(true);
    expect(showDemoChrome("dev")).toBe(true);
    expect(showDemoChrome("r1")).toBe(false);
    expect(showDemoChrome("full")).toBe(false);
  });
});

describe("isFormalDeliveryProfile", () => {
  it("r1 is formal delivery", () => {
    expect(isFormalDeliveryProfile("r1")).toBe(true);
    expect(isFormalDeliveryProfile("experience")).toBe(false);
  });
});

describe("getStepMilestone", () => {
  it("rfq has no milestone (R1 base)", () => {
    expect(getStepMilestone("rfq")).toBeNull();
  });

  it("returns correct milestone label for post-R1 steps", () => {
    expect(getStepMilestone("quote")).toBe("M3");
    expect(getStepMilestone("qa")).toBe("M4");
    expect(getStepMilestone("proposal")).toBe("M5");
  });
});
