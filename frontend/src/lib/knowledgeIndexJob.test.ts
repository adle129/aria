import { describe, expect, it } from "vitest";
import {
  ACTIVE_INDEX_JOB_STATUSES,
  INDEX_JOB_PHASE_LABEL,
  INDEX_JOB_STATUS_LABEL,
} from "./knowledgeIndexJob";

describe("knowledge index job labels", () => {
  it("distinguishes active and terminal states", () => {
    expect(ACTIVE_INDEX_JOB_STATUSES.has("queued")).toBe(true);
    expect(ACTIVE_INDEX_JOB_STATUSES.has("cancelling")).toBe(true);
    expect(ACTIVE_INDEX_JOB_STATUSES.has("completed")).toBe(false);
  });

  it("maps backend states and phases to user labels", () => {
    expect(INDEX_JOB_STATUS_LABEL.running).toBe("索引中");
    expect(INDEX_JOB_PHASE_LABEL.embedding).toContain("向量");
  });
});
