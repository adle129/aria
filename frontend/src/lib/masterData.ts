/** kb_admin customer / vehicle_model master data (R1-CHG05). */

export type MasterDataItem = {
  id: string;
  name: string;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export function masterDataSelectOptions(
  items: MasterDataItem[],
  opts?: { includeInactive?: boolean },
): Array<{ value: string; label: string; disabled?: boolean }> {
  const includeInactive = Boolean(opts?.includeInactive);
  return items
    .filter((item) => includeInactive || item.is_active)
    .map((item) => ({
      value: item.name,
      label: item.is_active ? item.name : `${item.name}（已停用）`,
      disabled: !item.is_active,
    }));
}
