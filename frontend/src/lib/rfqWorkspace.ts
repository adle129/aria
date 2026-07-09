import type { TaskPayload } from "@/types/task";

export type RfqWorkspaceStage =
  | "empty"
  | "processing"
  | "dimension_review"
  | "matrix"
  | "failed";

export const RFQ_BEGIN_NEW_EVENT = "aria-rfq-begin-new";
export const RFQ_BEGIN_NEW_FLAG = "aria_rfq_begin_new";

const IN_FLIGHT = new Set(["queued", "pending", "parsing", "retrieving", "generating"]);

export function resolveRfqWorkspaceStage(
  task: TaskPayload | null,
  options: { uploading: boolean; restoring: boolean; hasMatrix: boolean },
): RfqWorkspaceStage {
  const { uploading, restoring, hasMatrix } = options;
  if (restoring && !task) return "empty";
  if (uploading || (task && IN_FLIGHT.has(task.processing_status))) return "processing";
  if (!task) return "empty";
  if (task.processing_status === "failed") return "failed";
  if (task.processing_status === "dimension_review") return "dimension_review";
  if (task.processing_status === "completed" && hasMatrix) return "matrix";
  if (task.processing_status === "completed") return "matrix";
  return "empty";
}
