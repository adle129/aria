/** Parse API timestamps; naive UTC strings from Postgres are treated as UTC. */
export function parseApiTimestamp(iso?: string | null): number {
  if (!iso) return NaN;
  const trimmed = iso.trim();
  if (!trimmed) return NaN;
  const hasZone = /[zZ]$|[+-]\d{2}:\d{2}$/.test(trimmed);
  const normalized = hasZone ? trimmed : `${trimmed.replace(" ", "T")}Z`;
  return Date.parse(normalized);
}
