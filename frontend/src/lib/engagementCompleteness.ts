export type EngagementTier = "gold" | "silver" | "copper";

export const ENGAGEMENT_TIER_LABEL: Record<EngagementTier, string> = {
  gold: "金级",
  silver: "银级",
  copper: "铜级",
};

export const ENGAGEMENT_TIER_COLOR: Record<EngagementTier, string> = {
  gold: "green",
  silver: "blue",
  copper: "orange",
};

export const ENGAGEMENT_TIER_TIP: Record<EngagementTier, string> = {
  gold: "RFQ、Q&A 清单与人力报价齐全，可支持全部自动化能力。",
  silver: "仅缺人力报价，第二期 Excel 自动生成不可用。",
  copper: "缺少 Q&A 或多项资料；有可解析 RFQ 时仍可参与对标检索。",
};

export const ENGAGEMENT_INDEX_STATUS_LABEL: Record<string, string> = {
  indexed: "可检索",
  pending: "待更新",
  failed: "更新失败",
};

export const ENGAGEMENT_INDEX_STATUS_TIP: Record<string, string> = {
  indexed: "资料已就绪，可出现在 RFQ 相似项目结果中。",
  pending: "资料已变更或新上传，请点击「更新检索」后才会用于相似项目对标。",
  failed: "更新未成功，该项目暂时不会出现在相似检索中。",
};

export const ENGAGEMENT_INDEX_STATUS_COLOR: Record<string, string> = {
  indexed: "success",
  pending: "default",
  failed: "error",
};

export function formatEngagementTier(
  tier: string | null | undefined,
): { label: string; color?: string; tip?: string } {
  if (tier === "gold" || tier === "silver" || tier === "copper") {
    return {
      label: ENGAGEMENT_TIER_LABEL[tier],
      color: ENGAGEMENT_TIER_COLOR[tier],
      tip: ENGAGEMENT_TIER_TIP[tier],
    };
  }
  return {
    label: "待评估",
    color: "default",
    tip: "该项目尚未记录完整度。重新上传项目包或执行「更新知识库索引」后将自动显示。",
  };
}

export function formatEngagementIndexStatus(
  status: string,
  opts?: { lastError?: string | null },
): {
  label: string;
  color: string;
  tip: string;
} {
  const baseTip = ENGAGEMENT_INDEX_STATUS_TIP[status] ?? "项目检索更新状态。";
  const tip =
    status === "failed" && opts?.lastError
      ? `${baseTip} 原因：${opts.lastError}`
      : baseTip;
  return {
    label: ENGAGEMENT_INDEX_STATUS_LABEL[status] ?? status,
    color: ENGAGEMENT_INDEX_STATUS_COLOR[status] ?? "default",
    tip,
  };
}
