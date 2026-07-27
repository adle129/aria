export const ENGAGEMENT_FUNCTION_OPTIONS = [
  "PM",
  "Chassis",
  "BIW",
  "CAE",
  "EE",
  "Interior",
  "GI",
  "PS",
  "Test validation",
] as const;

export interface EngagementMetadataFields {
  project_name?: string | null;
  customer?: string | null;
  vehicle_model?: string | null;
  year?: number | null;
  functions?: string[] | null;
}

/** Year options for ingest form: last 20 years through next year. */
export function engagementYearOptions(
  now = new Date(),
): Array<{ value: number; label: string }> {
  const current = now.getFullYear();
  const start = current - 20;
  const end = current + 1;
  const years: Array<{ value: number; label: string }> = [];
  for (let y = end; y >= start; y -= 1) {
    years.push({ value: y, label: String(y) });
  }
  return years;
}

/** True when all required business metadata fields are present. */
export function isEngagementMetadataComplete(
  fields: EngagementMetadataFields,
): boolean {
  return Boolean(
    (fields.project_name || "").trim() &&
      (fields.customer || "").trim() &&
      fields.year != null &&
      (fields.functions || []).length > 0,
  );
}

export function formatEngagementMetadataSummary(
  fields: EngagementMetadataFields,
): string {
  const parts: string[] = [];
  if (fields.customer?.trim()) parts.push(fields.customer.trim());
  if (fields.vehicle_model?.trim()) parts.push(fields.vehicle_model.trim());
  if (fields.year != null) parts.push(String(fields.year));
  const fns = (fields.functions || []).filter(Boolean);
  if (fns.length) parts.push(fns.join(" / "));
  return parts.length ? parts.join(" · ") : "—";
}
