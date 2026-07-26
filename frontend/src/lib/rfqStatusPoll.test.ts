import { describe, expect, it } from "vitest";
import { resolveStatusWatchTaskId, RfqPollSessionMap } from "@/lib/rfqStatusPoll";

describe("RfqPollSessionMap", () => {
  it("keeps sibling task polls independent", () => {
    const sessions = new RfqPollSessionMap();
    const epochA = sessions.begin("task-a");
    const epochB = sessions.begin("task-b");

    expect(sessions.isCurrent("task-a", epochA)).toBe(true);
    expect(sessions.isCurrent("task-b", epochB)).toBe(true);
    expect(sessions.isActive("task-a")).toBe(true);
    expect(sessions.isActive("task-b")).toBe(true);
  });

  it("only invalidates the same task when begin is called again", () => {
    const sessions = new RfqPollSessionMap();
    const epochA1 = sessions.begin("task-a");
    const epochB = sessions.begin("task-b");
    const epochA2 = sessions.begin("task-a");

    expect(sessions.isCurrent("task-a", epochA1)).toBe(false);
    expect(sessions.isCurrent("task-a", epochA2)).toBe(true);
    expect(sessions.isCurrent("task-b", epochB)).toBe(true);
  });

  it("end only clears matching epoch", () => {
    const sessions = new RfqPollSessionMap();
    const epochA1 = sessions.begin("task-a");
    const epochA2 = sessions.begin("task-a");
    sessions.end("task-a", epochA1);
    expect(sessions.isActive("task-a")).toBe(true);
    sessions.end("task-a", epochA2);
    expect(sessions.isActive("task-a")).toBe(false);
  });

  it("invalidateAll cancels every active poll", () => {
    const sessions = new RfqPollSessionMap();
    const epochA = sessions.begin("task-a");
    const epochB = sessions.begin("task-b");
    sessions.invalidateAll();
    expect(sessions.isCurrent("task-a", epochA)).toBe(false);
    expect(sessions.isCurrent("task-b", epochB)).toBe(false);
    expect(sessions.isActive("task-a")).toBe(false);
    expect(sessions.isActive("task-b")).toBe(false);
  });

  it("invalidate stops one task without affecting siblings", () => {
    const sessions = new RfqPollSessionMap();
    const epochA = sessions.begin("task-a");
    const epochB = sessions.begin("task-b");
    sessions.invalidate("task-a");
    expect(sessions.isCurrent("task-a", epochA)).toBe(false);
    expect(sessions.isActive("task-a")).toBe(false);
    expect(sessions.isCurrent("task-b", epochB)).toBe(true);
  });
});

describe("resolveStatusWatchTaskId", () => {
  it("prefers the displayed task over a sibling active poll", () => {
    expect(
      resolveStatusWatchTaskId({
        displayedTaskId: "task-a",
        activePollTaskId: "task-b",
      }),
    ).toBe("task-a");
  });

  it("falls back to active poll when nothing is displayed", () => {
    expect(
      resolveStatusWatchTaskId({
        displayedTaskId: null,
        activePollTaskId: "task-b",
      }),
    ).toBe("task-b");
  });
});
