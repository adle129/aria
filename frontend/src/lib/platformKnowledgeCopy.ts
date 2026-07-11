/** Engineer-facing knowledge explainer copy (no infra jargon). */

export const ENGINEER_INTRO =
  "这里汇集历史项目的 RFQ、问答清单与报价资料，供你在「RFQ 分析」中查找相似项目、做技术对标。本页可查看资料覆盖、浏览项目清单，并试检索关键词。";

export const ENGINEER_FOOTER =
  "资料由资料库管理员维护。若对标结果偏少或覆盖不足，请联系管理员补充历史项目资料。";

export type EngineerUsageRow = {
  key: string;
  stage: string;
  help: string;
};

export const ENGINEER_USAGE_ROWS: EngineerUsageRow[] = [
  {
    key: "rfq",
    stage: "RFQ 分析",
    help: "推荐相似历史项目，辅助对比矩阵与维度确认",
  },
  {
    key: "baselines",
    stage: "人天参考",
    help: "查看历史报价中的人天基线，可对照源表",
  },
];

export const DEMO_ENGINEER_USAGE_ROWS: EngineerUsageRow[] = [
  {
    key: "rfq",
    stage: "RFQ 分析",
    help: "推荐相似历史项目，辅助对比与缺口提示",
  },
  {
    key: "qa",
    stage: "问答清单",
    help: "后续版本将支持查阅历史问题与参考依据",
  },
  {
    key: "quote",
    stage: "人力报价",
    help: "后续版本将支持查阅历史人天与岗位配置",
  },
];

export const ENGINEER_FORBIDDEN_TERMS = [
  "向量",
  "本地模型",
  "manifest",
  "不向量化",
  "R1 已交付",
  "合同里程碑",
  "检索引擎",
  "knowledge_base",
] as const;

export function engineerExplainerPlainText(showDemoChrome: boolean): string {
  const rows = showDemoChrome ? DEMO_ENGINEER_USAGE_ROWS : ENGINEER_USAGE_ROWS;
  const usage = rows.map((r) => `${r.stage}${r.help}`).join("");
  return `${ENGINEER_INTRO}${usage}${ENGINEER_FOOTER}`;
}
