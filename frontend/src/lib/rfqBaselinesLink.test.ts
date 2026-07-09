import { describe, expect, it } from "vitest";
import {
  buildBaselinesKnowledgeHref,
  resolveEngagementId,
  resolveProjectBaselinesEngagementIds,
} from "@/lib/rfqBaselinesLink";

describe("resolveEngagementId", () => {
  it("prefers engagement_id on project row", () => {
    expect(resolveEngagementId({ engagement_id: "eng-1", project_name: "A" }, [])).toBe("eng-1");
  });

  it("falls back to similar_projects metadata by project name", () => {
    const similar = [
      {
        project_name: "历史项目 B",
        metadata: { project_name: "历史项目 B", engagement_id: "eng-b" },
      },
    ];
    expect(resolveEngagementId({ project_name: "历史项目 B" }, similar)).toBe("eng-b");
  });

  it("returns null when no match", () => {
    expect(resolveEngagementId({ project_name: "X" }, [])).toBeNull();
  });
});

describe("buildBaselinesKnowledgeHref", () => {
  it("builds knowledge baselines deep link", () => {
    expect(buildBaselinesKnowledgeHref("eng-42")).toBe(
      "/knowledge?tab=baselines&engagement_id=eng-42",
    );
  });
});

describe("resolveProjectBaselinesEngagementIds", () => {
  it("maps each comparison project to engagement id", () => {
    const projects = [{ project_name: "P1" }, { engagement_id: "e2", project_name: "P2" }];
    const similar = [{ metadata: { project_name: "P1", engagement_id: "e1" } }];
    expect(resolveProjectBaselinesEngagementIds(projects, similar)).toEqual(["e1", "e2"]);
  });
});
