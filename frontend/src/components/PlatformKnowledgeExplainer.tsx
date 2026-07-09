"use client";

import { Collapse, Space, Table, Tag, Typography } from "antd";
import { useUiProfile } from "@/hooks/useUiProfile";

const { Paragraph, Text } = Typography;

type ConsumerRow = {
  key: string;
  consumer: string;
  status: string;
  statusColor: "processing" | "default" | "success";
  detail: string;
};

const DEMO_CONSUMER_ROWS: ConsumerRow[] = [
  {
    key: "quoting",
    consumer: "报价助手",
    status: "当前 Demo",
    statusColor: "processing" as const,
    detail: "RFQ 对标（已用同一检索引擎）；技术方案 / QA（Phase 2 接入）",
  },
  {
    key: "future",
    consumer: "更多应用",
    status: "平台扩展",
    statusColor: "default" as const,
    detail: "复用同一向量索引与本地模型，无需重复建库（正式版可按角色控制检索范围）",
  },
];

const R1_CONSUMER_ROWS: ConsumerRow[] = [
  {
    key: "quoting",
    consumer: "报价助手",
    status: "R1 已交付",
    statusColor: "success" as const,
    detail: "RFQ 全维度技术对标 + 历史项目检索；方案 / QA / Excel 报价为后续合同里程碑",
  },
  {
    key: "future",
    consumer: "更多应用",
    status: "平台扩展",
    statusColor: "default" as const,
    detail: "复用同一向量索引与本地模型；按角色控制检索与写权限",
  },
];

const DEMO_QUOTING_STAGE_ROWS = [
  {
    key: "rfq",
    stage: "RFQ 分析",
    usage: "相似项目、对比矩阵、Function 缺口提示",
    docTypes: "RFQ、方案摘要",
    phase: "当前 Demo",
  },
  {
    key: "qa",
    stage: "QA 清单",
    usage: "历史问题与参考依据",
    docTypes: "QA 清单",
    phase: "Phase 2",
  },
  {
    key: "quote",
    stage: "人力报价",
    usage: "历史人天与岗位配置参考",
    docTypes: "人力报价",
    phase: "Phase 2",
  },
];

const R1_QUOTING_STAGE_ROWS = [
  {
    key: "rfq",
    stage: "RFQ 分析",
    usage: "相似项目、对比矩阵、维度确认、人天基线参考",
    docTypes: "RFQ、Q_A（检索）",
    phase: "R1",
  },
  {
    key: "baselines",
    stage: "人天基线",
    usage: "历史报价 Excel 规则解析，可对照源表",
    docTypes: "人力报价",
    phase: "R1",
  },
];

export default function PlatformKnowledgeExplainer() {
  const { showDemoChrome } = useUiProfile();
  const consumerRows = showDemoChrome ? DEMO_CONSUMER_ROWS : R1_CONSUMER_ROWS;
  const stageRows = showDemoChrome ? DEMO_QUOTING_STAGE_ROWS : R1_QUOTING_STAGE_ROWS;

  return (
    <Collapse
      defaultActiveKey={showDemoChrome ? ["platform"] : []}
      style={{ marginBottom: 16 }}
      items={[
        {
          key: "platform",
          label: (
            <Space>
              <Text strong>平台说明</Text>
              <Tag color="blue">共享能力</Tag>
              <Text type="secondary">报价助手如何使用本库</Text>
            </Space>
          ),
          children: (
            <>
              <Paragraph type="secondary" style={{ marginTop: 0 }}>
                本页管理的是 ARIA <Text strong>平台知识库</Text>
                （历史项目 RFQ、Q_A、人力报价等工程资料）。报价工程师在「RFQ
                分析」完成对标；资料库管理员在此完成 Engagement 入库、索引与检索验证。
              </Paragraph>

              <Table
                size="small"
                pagination={false}
                style={{ marginBottom: 16 }}
                rowKey="key"
                dataSource={consumerRows}
                columns={[
                  { title: "消费方", dataIndex: "consumer", width: 120 },
                  {
                    title: "状态",
                    dataIndex: "status",
                    width: 110,
                    render: (v: string, row) => <Tag color={row.statusColor}>{v}</Tag>,
                  },
                  { title: "说明", dataIndex: "detail" },
                ]}
              />

              <Text strong>报价助手消费路径</Text>
              <Table
                size="small"
                pagination={false}
                style={{ marginTop: 8, marginBottom: 16 }}
                rowKey="key"
                dataSource={stageRows}
                columns={[
                  { title: "报价环节", dataIndex: "stage", width: 100 },
                  { title: "检索用途", dataIndex: "usage" },
                  { title: "资料类型", dataIndex: "docTypes", width: 140 },
                  {
                    title: "阶段",
                    dataIndex: "phase",
                    width: 100,
                    render: (v: string) => (
                      <Tag color={v === "R1" ? "blue" : v === "当前 Demo" ? "green" : "default"}>{v}</Tag>
                    ),
                  },
                ]}
              />

              <Text strong>Engagement 项目包</Text>
              <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 8 }}>
                一次完整报价项目通常包含 RFQ、Q_A 清单、人力报价 Excel 等。通过{" "}
                <Text strong>Engagement</Text> 与 <Text code>manifest.json</Text>{" "}
                建立关联；RFQ 与 Q_A 进入向量检索，报价 Excel 解析为人天基线（不向量化）。
                {showDemoChrome
                  ? " Demo 环境部分能力为占位；正式 R1 支持 Web 上传与 IT 目录批量入库。"
                  : " 支持 IT 目录批量入库与本页 Web 上传（单次最多 5 套）。"}
              </Paragraph>
              <Paragraph
                type="secondary"
                style={{
                  marginBottom: 0,
                  fontFamily: "monospace",
                  fontSize: 12,
                  whiteSpace: "pre",
                  background: "#fafafa",
                  padding: 12,
                  borderRadius: 4,
                }}
              >
                {`knowledge_base/<engagement_id>/
  ├── manifest.json
  ├── RFQ_xxx.docx
  ├── Q_A_xxx.xlsx
  └── Quote_xxx.xlsx   ← 规则解析 → manpower_baselines`}
              </Paragraph>
            </>
          ),
        },
      ]}
    />
  );
}
