import { describe, expect, it } from "vitest";
import { resolveRfqWorkspaceStage } from "@/lib/rfqWorkspace";

describe("resolveRfqWorkspaceStage", () => {
  it("returns empty when no task", () => {
    expect(resolveRfqWorkspaceStage(null, { uploading: false, restoring: false, hasMatrix: false })).toBe(
      "empty",
    );
  });

  it("returns processing when uploading", () => {
    expect(
      resolveRfqWorkspaceStage(
        { task_id: "1", processing_status: "completed", status: "draft" },
        { uploading: true, restoring: false, hasMatrix: true },
      ),
    ).toBe("processing");
  });

  it("returns dimension_review", () => {
    expect(
      resolveRfqWorkspaceStage(
        { task_id: "1", processing_status: "dimension_review", status: "draft" },
        { uploading: false, restoring: false, hasMatrix: false },
      ),
    ).toBe("dimension_review");
  });

  it("returns matrix when completed with rows", () => {
    expect(
      resolveRfqWorkspaceStage(
        { task_id: "1", processing_status: "completed", status: "draft" },
        { uploading: false, restoring: false, hasMatrix: true },
      ),
    ).toBe("matrix");
  });

  it("returns cancelled for cancelled tasks", () => {
    expect(
      resolveRfqWorkspaceStage(
        { task_id: "1", processing_status: "cancelled", status: "draft" },
        { uploading: false, restoring: false, hasMatrix: false },
      ),
    ).toBe("cancelled");
  });

  it("returns processing for cancelling tasks", () => {
    expect(
      resolveRfqWorkspaceStage(
        { task_id: "1", processing_status: "cancelling", status: "draft" },
        { uploading: false, restoring: false, hasMatrix: false },
      ),
    ).toBe("processing");
  });
});
