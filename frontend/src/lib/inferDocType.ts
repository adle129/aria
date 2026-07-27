/** Infer knowledge doc_type from filename (aligned with backend classify_corpus_file). */

export type InferredDocType = "rfq" | "qa" | "quote_manpower" | "summary";

export const INFER_DOC_TYPE_HINT =
  "无法识别文件类型。请使用文件名含 RFQ（.doc/.docx）、Q_A（.xlsx）或「报价」「人力」（.xlsx）的文件。";

export function inferDocTypeFromFilename(filename: string): InferredDocType | null {
  const name = filename.trim();
  if (!name) return null;
  const upper = name.toUpperCase();
  const ext = name.includes(".")
    ? `.${name.split(".").pop()!.toLowerCase()}`
    : "";

  if (upper.includes("RFQ") && (ext === ".doc" || ext === ".docx")) {
    return "rfq";
  }
  if (upper.includes("Q_A") && ext === ".xlsx") {
    return "qa";
  }
  if (ext === ".xlsx" && (name.includes("人力") || name.includes("报价"))) {
    return "quote_manpower";
  }
  if (ext === ".pdf" || ext === ".pptx") {
    return "summary";
  }
  return null;
}
