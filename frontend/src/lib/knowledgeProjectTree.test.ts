import { describe, expect, it } from "vitest";
import { buildKnowledgeProjectTree } from "./knowledgeProjectTree";

describe("buildKnowledgeProjectTree", () => {
  it("nests documents under engagement_id", () => {
    const tree = buildKnowledgeProjectTree(
      [
        {
          engagement_id: "e1",
          project_name: "Proj A",
          index_status: "indexed",
          folder_path: "e1",
          customer: "OEM",
          year: 2024,
          functions: ["PM"],
        },
      ],
      [
        {
          path: "e1/rfq.docx",
          project_name: "Proj A",
          doc_type: "rfq",
          status: "indexed",
          engagement_id: "e1",
        },
        {
          path: "e1/qa.xlsx",
          project_name: "Proj A",
          doc_type: "qa",
          status: "pending",
          engagement_id: "e1",
        },
      ],
    );
    expect(tree).toHaveLength(1);
    expect(tree[0].documents).toHaveLength(2);
    expect(tree[0].synthetic).toBe(false);
  });

  it("overrides stale indexed docs when engagement is pending", () => {
    const tree = buildKnowledgeProjectTree(
      [
        {
          engagement_id: "e1",
          project_name: "Proj A",
          index_status: "pending",
          folder_path: "e1",
        },
      ],
      [
        {
          path: "e1/qa.xlsx",
          project_name: "Proj A",
          doc_type: "qa",
          status: "indexed",
          engagement_id: "e1",
        },
      ],
    );
    expect(tree[0].documents[0].status).toBe("pending");
  });

  it("creates synthetic parent for orphan documents", () => {
    const tree = buildKnowledgeProjectTree(
      [],
      [
        {
          path: "x/rfq.docx",
          project_name: "Loose",
          doc_type: "rfq",
          status: "indexed",
        },
      ],
    );
    expect(tree).toHaveLength(1);
    expect(tree[0].synthetic).toBe(true);
    expect(tree[0].project_name).toBe("Loose");
    expect(tree[0].documents).toHaveLength(1);
  });
});
