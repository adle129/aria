/** Join engagements + documents for knowledge inventory (frontend-only). */

export type KnowledgeDocRow = {
  path: string;
  project_name: string;
  doc_type: string;
  status: string;
  file_size_bytes?: number;
  /** Disk mtime from API; shown as 文件时间. */
  modified_at?: string | null;
  error?: string;
  engagement_id?: string;
  customer?: string | null;
  year?: number | null;
  functions?: string[];
  metadata_summary?: string | null;
};

export type KnowledgeEngagementRow = {
  engagement_id: string;
  project_name: string;
  customer?: string | null;
  vehicle_model?: string | null;
  year?: number | null;
  functions?: string[];
  metadata_complete?: boolean;
  tier?: string | null;
  index_status: string;
  content_hash?: string | null;
  uploaded_at?: string | null;
  last_indexed_at?: string | null;
  last_error?: string | null;
  folder_path: string;
  space_id?: string | null;
  has_hard_refs?: boolean;
  /** Unarchived RFQ task ids that hard-reference this engagement. */
  ref_task_ids?: string[];
  document_count?: number;
  deletable?: boolean;
};

export type KnowledgeProjectTreeRow = KnowledgeEngagementRow & {
  documents: KnowledgeDocRow[];
  /** True when synthesized from documents only (no engagements API row). */
  synthetic?: boolean;
};

function docKey(doc: KnowledgeDocRow): string {
  if (doc.engagement_id) return `id:${doc.engagement_id}`;
  return `name:${String(doc.project_name || "").trim() || "—"}`;
}

/**
 * Parent = engagement (or synthetic project from orphan docs).
 * Children = documents matched by engagement_id, else project_name.
 */
export function buildKnowledgeProjectTree(
  engagements: KnowledgeEngagementRow[],
  documents: KnowledgeDocRow[],
): KnowledgeProjectTreeRow[] {
  const byId = new Map<string, KnowledgeDocRow[]>();
  const byName = new Map<string, KnowledgeDocRow[]>();
  const assigned = new Set<KnowledgeDocRow>();

  for (const doc of documents) {
    if (doc.engagement_id) {
      const list = byId.get(doc.engagement_id) || [];
      list.push(doc);
      byId.set(doc.engagement_id, list);
    }
    const name = String(doc.project_name || "").trim();
    if (name) {
      const list = byName.get(name) || [];
      list.push(doc);
      byName.set(name, list);
    }
  }

  const rows: KnowledgeProjectTreeRow[] = [];
  const usedDocKeys = new Set<string>();

  for (const eng of engagements) {
    const fromId = byId.get(eng.engagement_id) || [];
    const fromName =
      fromId.length > 0 ? [] : byName.get(String(eng.project_name || "").trim()) || [];
    const docs = fromId.length > 0 ? fromId : fromName;
    for (const d of docs) {
      assigned.add(d);
      usedDocKeys.add(docKey(d));
    }
    // Project pending/failed wins over stale path-based「可检索」after replace.
    const syncedDocs =
      eng.index_status === "pending" || eng.index_status === "failed"
        ? docs.map((d) => ({ ...d, status: eng.index_status }))
        : docs;
    rows.push({
      ...eng,
      documents: syncedDocs,
      synthetic: false,
    });
  }

  const orphanGroups = new Map<string, KnowledgeDocRow[]>();
  for (const doc of documents) {
    if (assigned.has(doc)) continue;
    const key = docKey(doc);
    if (usedDocKeys.has(key) && engagements.some((e) => e.engagement_id === doc.engagement_id)) {
      continue;
    }
    const list = orphanGroups.get(key) || [];
    list.push(doc);
    orphanGroups.set(key, list);
  }

  for (const [, docs] of orphanGroups) {
    const head = docs[0];
    const eid =
      head.engagement_id ||
      `orphan:${String(head.project_name || "unknown").trim() || "unknown"}`;
    rows.push({
      engagement_id: eid,
      project_name: head.project_name || "未命名项目",
      customer: head.customer,
      year: head.year,
      functions: head.functions,
      metadata_complete: undefined,
      tier: null,
      index_status: docs.every((d) => d.status === "indexed")
        ? "indexed"
        : docs.some((d) => d.status === "failed")
          ? "failed"
          : "pending",
      folder_path: "",
      documents: docs,
      synthetic: true,
    });
  }

  return rows.sort((a, b) =>
    String(a.project_name).localeCompare(String(b.project_name), "zh"),
  );
}
