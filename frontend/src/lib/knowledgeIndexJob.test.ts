import { describe, expect, it } from "vitest";
import {
  ACTIVE_INDEX_JOB_STATUSES,
  getKnowledgeIndexFailureGuidance,
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

  it("provides actionable guidance without exposing server paths", () => {
    const guidance = getKnowledgeIndexFailureGuidance({
      path: "/app/data/knowledge_base/mock_project_1",
      error: "RFQ 解析失败 — 未找到 RFQ*.doc/docx",
    });

    expect(guidance.itemName).toBe("mock_project_1");
    expect(guidance.impact).toContain("未进入本次生效索引");
    expect(guidance.action).toContain("替换同 ID 项目");
    expect(guidance.action).toContain("再次更新索引");
    expect(JSON.stringify(guidance)).not.toContain("/app/data");
  });

  it("provides a generic recovery action for unknown failures", () => {
    const guidance = getKnowledgeIndexFailureGuidance({
      path: String.raw`C:\upload\project-a`,
      error: "处理超时",
    });

    expect(guidance.itemName).toBe("project-a");
    expect(guidance.reason).toBe("处理超时");
    expect(guidance.action).toContain("管理员");
  });
});
