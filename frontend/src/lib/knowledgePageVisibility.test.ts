import { describe, expect, it } from "vitest";
import {
  getKnowledgePageVisibility,
  knowledgeCoverageHint,
  knowledgeDocumentsEmptyText,
  knowledgePageIntro,
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
    expect(v.showIngestWizard).toBe(false);
    expect(v.showUpload).toBe(false);
    expect(v.showIndexJob).toBe(false);
    expect(v.showCapacityAlert).toBe(false);
    expect(v.showImportAudit).toBe(false);
    expect(v.showOpsMockRagAlert).toBe(false);
    expect(v.showEngagementInventory).toBe(true);
  });

  it("shows full admin console for kb_admin on formal profile", () => {
    const v = getKnowledgePageVisibility({
      authEnabled: true,
      isKbAdmin: true,
      isFormalDelivery: true,
    });
    expect(v.canWriteKb).toBe(true);
    expect(v.showIngestWizard).toBe(true);
    expect(v.showUpload).toBe(true);
    expect(v.showIndexJob).toBe(true);
    expect(v.showImportAudit).toBe(true);
    expect(v.showEngagementInventory).toBe(true);
    expect(v.showOpsMockRagAlert).toBe(true);
  });

  it("treats auth-disabled as writable (local/dev)", () => {
    const v = getKnowledgePageVisibility({
      authEnabled: false,
      isKbAdmin: false,
      isFormalDelivery: false,
    });
    expect(v.canWriteKb).toBe(true);
    expect(v.showIngestWizard).toBe(true);
    expect(v.showEngagementInventory).toBe(false);
    expect(v.showImportAudit).toBe(false);
  });
});

describe("knowledge page copy helpers", () => {
  it("keeps engineer intro free of ingest CTA", () => {
    expect(knowledgePageIntro(false)).not.toMatch(/入库与索引/);
    expect(knowledgePageIntro(true)).toMatch(/入库与索引/);
  });

  it("does not tell engineers to upload packages", () => {
    const empty = knowledgeDocumentsEmptyText({
      canWriteKb: false,
      showDemoChrome: false,
    });
    expect(empty).not.toMatch(/上传项目包/);
    expect(empty).toMatch(/资料库管理员|IT/);
  });

  it("softens coverage and search hints for read-only users", () => {
    expect(knowledgeCoverageHint(false)).toMatch(/人工核对/);
    expect(knowledgeCoverageHint(false)).not.toMatch(/优先补充/);
    expect(knowledgeSearchHint(false)).toMatch(/试检索/);
    expect(knowledgeSearchHint(true)).toMatch(/验证/);
  });
});
