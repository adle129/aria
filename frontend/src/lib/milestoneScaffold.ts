import type { QuotingStep } from "@/lib/uiProfile";

export type MilestoneScaffoldStep = Exclude<QuotingStep, "rfq">;

export interface MilestoneScaffoldContent {
  title: string;
  milestone: string;
  subtitle: string;
  deliverables: string[];
  wireframeHint: string;
}

export const MILESTONE_SCAFFOLD: Record<MilestoneScaffoldStep, MilestoneScaffoldContent> = {
  quote: {
    title: "人力报价",
    milestone: "M3",
    subtitle: "基于 ScopeMatch 与历史 baselines，生成 9 个 Function 的人力报价 Excel。",
    deliverables: [
      "ScopeMatch：为当前 RFQ 匹配最相似历史项目",
      "9 Function 月列人天预填（PM / Chassis / BIW / …）",
      "quote_fill_report：缺口与需人工复核项",
      "导出报价人力_*.xlsx，工程师在 Excel 中终稿",
    ],
    wireframeHint: "确认导出 · 生成 Excel · 人天分解预览",
  },
  qa: {
    title: "QA 清单",
    milestone: "M4",
    subtitle: "合并 Top-3 历史 Q_A，去重与影响分类后导出 8 列 Excel（不在网页内编辑）。",
    deliverables: [
      "Top-3 历史项目 Q_A Area 合并",
      "dedupe + 影响分类（高/中/低）",
      "8 列 Q_A 模板导出（Author / Answer 等留空供工程师填写）",
      "下载 Q_A_*.xlsx",
    ],
    wireframeHint: "生成清单 · 下载 Excel · 澄清问题表",
  },
  proposal: {
    title: "方案草案",
    milestone: "M5",
    subtitle: "按 34 页 Content Template 预填技术方案 PPT，并输出缺口报告。",
    deliverables: [
      "RFQ 开发范围 ↔ slide 映射预填",
      "34 页 .pptx 技术正文框架（非 LLM 自由撰写）",
      "proposal_fill_report：未覆盖 scope / 需人工补充页",
      "下载方案 PPT 供工程师终稿",
    ],
    wireframeHint: "生成 PPT · 模块摘要 · 缺口报告",
  },
};
