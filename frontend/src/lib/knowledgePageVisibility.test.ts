import { describe, expect, it } from "vitest";
import {
  canAccessPlatformKnowledgeNav,
  getKnowledgePageVisibility,
  knowledgeCoverageHint,
  knowledgeDocumentsEmptyText,
  knowledgePageIntro,
  knowledgePageTitle,
  knowledgeSearchHint,
} from "./knowledgePageVisibility";

describe("getKnowledgePageVisibility", () => {
  it("hides admin ingest surfaces for quote engineer", () => {
    const v = getKnowledgePageVisibility({
      authEnabled: true,
      isKbAdmin: false,
      isFormalDelivery: true,
    });
    expect(v.canWriteKb).toBe(false);
    expect(v.showUpload).toBe(false);
    expect(v.showIndexJob).toBe(false);
    expect(v.showCapacityAlert).toBe(false);
    expect(v.showOpsMockRagAlert).toBe(false);
    expect(v.showEngagementInventory).toBe(true);
    expect(v.showTrash).toBe(false);
  });

  it("shows list-centric admin console for kb_admin on formal profile", () => {
    const v = getKnowledgePageVisibility({
      authEnabled: true,
      isKbAdmin: true,
      isFormalDelivery: true,
    });
    expect(v.canWriteKb).toBe(true);
    expect(v.showUpload).toBe(true);
    expect(v.showIndexJob).toBe(true);
    expect(v.showEngagementInventory).toBe(true);
    expect(v.showOpsMockRagAlert).toBe(true);
    expect(v.showTrash).toBe(true);
  });

  it("treats auth-disabled as writable (local/dev)", () => {
    const v = getKnowledgePageVisibility({
      authEnabled: false,
      isKbAdmin: false,
      isFormalDelivery: false,
    });
    expect(v.canWriteKb).toBe(true);
    expect(v.showUpload).toBe(true);
    expect(v.showEngagementInventory).toBe(false);
    expect(v.showTrash).toBe(true);
  });
});

describe("canAccessPlatformKnowledgeNav", () => {
  it("hides knowledge nav for quote engineer when auth is on", () => {
    expect(
      canAccessPlatformKnowledgeNav({ authEnabled: true, isKbAdmin: false }),
    ).toBe(false);
  });

  it("shows knowledge nav for kb_admin when auth is on", () => {
    expect(
      canAccessPlatformKnowledgeNav({ authEnabled: true, isKbAdmin: true }),
    ).toBe(true);
  });

  it("shows knowledge nav when auth is disabled (local/dev)", () => {
    expect(
      canAccessPlatformKnowledgeNav({ authEnabled: false, isKbAdmin: false }),
    ).toBe(true);
  });
});

describe("knowledge page copy helpers", () => {
  it("keeps 知识库 as the primary product name", () => {
    expect(knowledgePageTitle(true)).toBe("知识库");
    expect(knowledgePageTitle(false)).toBe("知识库");
  });

  it("keeps engineer intro free of ingest CTA", () => {
    expect(knowledgePageIntro(false)).not.toMatch(/添加历史项目/);
    expect(knowledgePageIntro(true)).toMatch(/添加历史项目/);
    expect(knowledgePageIntro(true)).toMatch(/更新检索/);
    expect(knowledgePageIntro(true)).toMatch(/报价资料库/);
  });

  it("does not tell engineers to upload packages", () => {
    const empty = knowledgeDocumentsEmptyText({
      canWriteKb: false,
      showDemoChrome: false,
    });
    expect(empty).not.toMatch(/添加历史项目/);
    expect(empty).toMatch(/资料库管理员|IT/);
  });

  it("softens coverage and search hints for read-only users", () => {
    expect(knowledgeCoverageHint(false)).toMatch(/人工核对/);
    expect(knowledgeCoverageHint(false)).not.toMatch(/优先补充/);
    expect(knowledgeSearchHint(false)).toMatch(/聚合/);
    expect(knowledgeSearchHint(true)).toMatch(/聚合/);
  });
});
