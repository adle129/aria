import { describe, expect, it } from "vitest";
import {
  buildKnowledgeDownloadFilename,
  parseContentDispositionFilename,
  withTaskIdInFilename,
} from "./knowledgeDownloadFilename";

describe("knowledgeDownloadFilename", () => {
  it("prefers filename* over filename", () => {
    const cd =
      'attachment; filename="RFQ_.doc"; filename*=utf-8\'\'RFQ_%E6%A8%A1%E6%9D%BF__task-abc.doc';
    expect(parseContentDispositionFilename(cd)).toBe("RFQ_模板__task-abc.doc");
  });

  it("always injects task_id even when disposition has original name only", () => {
    const name = buildKnowledgeDownloadFilename({
      disposition: 'attachment; filename="RFQ_模板.doc"',
      engagementId: "test",
      docType: "rfq",
      taskId: "task-9",
    });
    expect(name).toBe("RFQ_模板__task-task-9.doc");
  });

  it("does not double-append task_id", () => {
    expect(withTaskIdInFilename("RFQ__task-old.doc", "new")).toBe(
      "RFQ__task-new.doc",
    );
  });
});
