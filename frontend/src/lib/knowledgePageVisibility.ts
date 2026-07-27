export type KnowledgePageRoleInput = {
  authEnabled: boolean;
  isKbAdmin: boolean;
  isFormalDelivery: boolean;
};

export type KnowledgePageVisibility = {
  canWriteKb: boolean;
  showCapacityAlert: boolean;
  showUpload: boolean;
  showIndexJob: boolean;
  showEngagementInventory: boolean;
  showOpsMockRagAlert: boolean;
  /** Recycle bin tab — kb_admin / auth-off only (R1-CHG09). */
  showTrash: boolean;
};

/** Role × profile → which /knowledge sections render. */
export function getKnowledgePageVisibility(
  input: KnowledgePageRoleInput,
): KnowledgePageVisibility {
  const canWriteKb = !input.authEnabled || input.isKbAdmin;
  return {
    canWriteKb,
    showCapacityAlert: canWriteKb,
    showUpload: canWriteKb,
    showIndexJob: canWriteKb,
    showEngagementInventory: input.isFormalDelivery,
    showOpsMockRagAlert: canWriteKb,
    showTrash: canWriteKb,
  };
}

/**
 * Platform knowledge nav / route access (R1-CHG01).
 * Auth off → show (local/dev). Auth on → kb_admin only; quote_engineer stays on RFQ.
 */
export function canAccessPlatformKnowledgeNav(input: {
  authEnabled: boolean;
  isKbAdmin: boolean;
}): boolean {
  if (!input.authEnabled) return true;
  return input.isKbAdmin;
}

export function knowledgePageIntro(canWriteKb: boolean): string {
  const base =
    "当前为报价资料库。按历史项目集中管理资料；日常对标结果在「RFQ 分析」查看";
  return canWriteKb
    ? `${base}。添加历史项目：上传资料 → 完善信息 → 更新检索。`
    : `${base}。`;
}

export function knowledgePageTitle(_canWriteKb?: boolean): string {
  return "知识库";
}

export function knowledgeDocumentsEmptyText(opts: {
  canWriteKb: boolean;
  showDemoChrome: boolean;
}): string {
  if (!opts.canWriteKb) {
    return "暂无文档；资料入库由资料库管理员或 IT 完成，完成后可在此查看与检索。";
  }
  if (opts.showDemoChrome) {
    return "暂无文档；可点击「添加历史项目」或由 IT 将项目包放入 knowledge_base/<项目名>/";
  }
  return "暂无文档；请点击「添加历史项目」或由 IT 目录落盘后更新检索";
}

export function knowledgeCoverageHint(canWriteKb: boolean): string {
  if (canWriteKb) {
    return "覆盖偏低的领域，建议在 RFQ 对标时重点人工补充依据，或优先补充该类历史项目资料。";
  }
  return "覆盖偏低的领域，RFQ 对标时请重点人工核对结论与依据。";
}

export function knowledgeSearchHint(canWriteKb: boolean): string {
  if (canWriteKb) {
    return "与「RFQ 分析」相似项目使用同一检索逻辑；结果按历史项目聚合，可展开查看出处。";
  }
  return "与「RFQ 分析」相似项目使用同一检索逻辑；列表按历史项目聚合，可展开查看出处。";
}
