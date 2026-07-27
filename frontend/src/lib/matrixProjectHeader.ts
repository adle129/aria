/** Matrix column header fields (R1-CHG02). */

import { formatProjectIdLine } from "@/lib/projectIdentity";

export type MatrixProjectHeader = {
  project_name: string;
  customer: string;
  vehicle_model: string;
  /** System engagement id — shown as 项目编号 for disambiguation. */
  engagement_id?: string | null;
};

const VEHICLE_DIM_KEYS = [
  "车型",
  "平台类型",
  "平台",
  "vehicle",
  "vehicle_model",
  "platform_type",
];

function cellText(cell: unknown): string | null {
  if (cell == null) return null;
  if (typeof cell === "string") {
    const t = cell.trim();
    return t || null;
  }
  if (typeof cell === "number" || typeof cell === "boolean") {
    return String(cell);
  }
  if (typeof cell === "object") {
    const value = (cell as { value?: unknown }).value;
    if (value != null) {
      const t = String(value).trim();
      return t || null;
    }
  }
  return null;
}

/** Prefer dimension values (平台类型/车型…); fall back to top-level fields. */
export function resolveVehicleModel(project: Record<string, unknown>): string | null {
  const dims = project.dimensions;
  if (dims && typeof dims === "object" && !Array.isArray(dims)) {
    for (const key of VEHICLE_DIM_KEYS) {
      const text = cellText((dims as Record<string, unknown>)[key]);
      if (text) return text;
    }
  }
  for (const key of ["vehicle_model", "platform_type", "vehicle"]) {
    const text = cellText(project[key]);
    if (text) return text;
  }
  return null;
}

export function buildMatrixProjectHeaders(
  projects: Array<Record<string, unknown>>,
): MatrixProjectHeader[] {
  return projects.map((p) => {
    const name = String(p.project_name || "").trim() || "历史项目";
    const customerRaw = p.customer != null ? String(p.customer).trim() : "";
    const vehicle = resolveVehicleModel(p);
    const eid = p.engagement_id != null ? String(p.engagement_id).trim() : "";
    return {
      project_name: name,
      customer: customerRaw || "—",
      vehicle_model: vehicle || "—",
      engagement_id: eid || null,
    };
  });
}

export function formatMatrixHeaderTooltip(h: MatrixProjectHeader): string {
  const idLine = formatProjectIdLine(h.engagement_id);
  const base = `${h.project_name} · ${h.customer} · ${h.vehicle_model}`;
  return idLine ? `${base}\n${idLine}` : base;
}

export function truncateHeaderText(text: string, max = 18): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max)}…`;
}
