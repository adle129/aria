export type KnowledgePageRoleInput = {
  authEnabled: boolean;
  isKbAdmin: boolean;
  isFormalDelivery: boolean;
};

export type KnowledgePageVisibility = {
  canWriteKb: boolean;
  showIngestWizard: boolean;
  showCapacityAlert: boolean;
  showUpload: boolean;
  showIndexJob: boolean;
  showImportAudit: boolean;
  showEngagementInventory: boolean;
  showOpsMockRagAlert: boolean;
};

/** Role × profile → which /knowledge sections render. */
export function getKnowledgePageVisibility(
  input: KnowledgePageRoleInput,
): KnowledgePageVisibility {
  const canWriteKb = !input.authEnabled || input.isKbAdmin;
  return {
    canWriteKb,
    showIngestWizard: canWriteKb,
    showCapacityAlert: canWriteKb,
    showUpload: canWriteKb,
    showIndexJob: canWriteKb,
    showImportAudit: canWriteKb && input.isFormalDelivery,
    showEngagementInventory: input.isFormalDelivery,
    showOpsMockRagAlert: canWriteKb,
  };
}

export function knowledgePageIntro(canWriteKb: boolean): string {
  const base =
    "历史项目 RFQ、方案、报价等工程资料 · 平台共享检索底座。日常在「RFQ 分析」查看对标结果；本页可检索与查看统计";
  return canWriteKb ? `${base}，并完成入库与索引。` : `${base}。`;
}

export function knowledgeDocumentsEmptyText(opts: {
  canWriteKb: boolean;
  showDemoChrome: boolean;
}): string {
  if (!opts.canWriteKb) {
    return "暂无文档；资料入库由资料库管理员或 IT 完成，完成后可在此查看与检索。";
  }
  if (opts.showDemoChrome) {
    return "暂无文档；可将项目包放入 knowledge_base/<项目名>/ 或本页「上传项目包」";
  }
  return "暂无文档；请通过 IT 目录入库或本页「上传项目包」添加 Engagement";
}

export function knowledgeCoverageHint(canWriteKb: boolean): string {
  if (canWriteKb) {
    return "覆盖偏低的领域，建议在 RFQ 对标时重点人工补充依据，或优先补充该类历史项目资料。";
  }
  return "覆盖偏低的领域，RFQ 对标时请重点人工核对结论与依据。";
}

export function knowledgeSearchHint(canWriteKb: boolean): string {
  if (canWriteKb) {
    return "RFQ 分析页中的「相似历史项目」由相同检索逻辑产生，可在此验证关键词能否命中预期资料。";
  }
  return "与「RFQ 分析」相似项目使用同一检索逻辑。可在此试检索，确认关键词能否命中历史资料。";
}
