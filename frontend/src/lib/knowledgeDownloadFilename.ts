/** Build local save name for knowledge source downloads (R1-CHG06). */

export function parseContentDispositionFilename(
  disposition: string | undefined | null,
): string | null {
  const raw = String(disposition || "").trim();
  if (!raw) return null;

  const star = /filename\*=(?:UTF-8''|utf-8'')([^;]+)/i.exec(raw);
  if (star?.[1]) {
    try {
      return decodeURIComponent(star[1].trim().replace(/^"|"$/g, ""));
    } catch {
      /* fall through */
    }
  }

  const quoted = /filename="([^"]+)"/i.exec(raw);
  if (quoted?.[1]) return quoted[1];

  const plain = /filename=([^;]+)/i.exec(raw);
  if (plain?.[1]) return plain[1].trim().replace(/^"|"$/g, "");

  return null;
}

export function withTaskIdInFilename(
  filename: string,
  taskId: string | null | undefined,
): string {
  const name = (filename || "download").replace(/[/\\]/g, "_").trim() || "download";
  const tid = (taskId || "").trim();
  const stripped = name
    .replace(/__task-[^./\\]+(?=\.[^./\\]+$)/i, "")
    .replace(/__task-[^./\\]+$/i, "");
  if (!tid) return stripped;
  const safeTid = tid.replace(/[/\\:]/g, "_").replace(/\.\./g, "_");
  const dot = stripped.lastIndexOf(".");
  if (dot > 0) {
    return `${stripped.slice(0, dot)}__task-${safeTid}${stripped.slice(dot)}`;
  }
  return `${stripped}__task-${safeTid}`;
}

export function buildKnowledgeDownloadFilename(opts: {
  disposition?: string | null;
  engagementId: string;
  docType: string;
  taskId?: string | null;
}): string {
  const fromHeader = parseContentDispositionFilename(opts.disposition);
  const fallback = `${opts.engagementId}_${opts.docType}`;
  return withTaskIdInFilename(fromHeader || fallback, opts.taskId);
}
