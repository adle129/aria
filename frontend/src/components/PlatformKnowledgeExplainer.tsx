"use client";

import { Collapse, Space, Table, Tag, Typography } from "antd";

const { Paragraph, Text } = Typography;

const CONSUMER_ROWS = [
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

const QUOTING_STAGE_ROWS = [
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

/** Collapsible platform narrative: shared KB consumed by quoting (and future apps). */
export default function PlatformKnowledgeExplainer() {
  return (
    <Collapse
      defaultActiveKey={["platform"]}
      style={{ marginBottom: 16 }}
      items={[
        {
          key: "platform",
          label: (
            <Space>
              <Text strong>平台说明</Text>
              <Tag color="blue">共享能力</Tag>
              <Text type="secondary">报价助手如何使用本库 · 未来应用扩展路径</Text>
            </Space>
          ),
          children: (
            <>
              <Paragraph type="secondary" style={{ marginTop: 0 }}>
                本页管理的是 ARIA <Text strong>平台知识库</Text>
                （历史项目 RFQ、方案、报价等工程资料），不是报价助手私有文件夹。报价工程师日常在「RFQ
                分析」查看对标结果即可；管理员在此完成入库、索引与检索验证。
              </Paragraph>

              <Table
                size="small"
                pagination={false}
                style={{ marginBottom: 16 }}
                rowKey="key"
                dataSource={CONSUMER_ROWS}
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
                dataSource={QUOTING_STAGE_ROWS}
                columns={[
                  { title: "报价环节", dataIndex: "stage", width: 100 },
                  { title: "检索用途", dataIndex: "usage" },
                  { title: "资料类型", dataIndex: "docTypes", width: 120 },
                  {
                    title: "阶段",
                    dataIndex: "phase",
                    width: 100,
                    render: (v: string) =>
                      v === "当前 Demo" ? <Tag color="green">{v}</Tag> : <Tag>{v}</Tag>,
                  },
                ]}
              />

              <Text strong>历史项目 Package（Phase 2）</Text>
              <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 8 }}>
                一次完整报价项目通常包含 RFQ、QA 清单、人力报价 Excel、技术方案等多份文件。正式版通过{" "}
                <Text strong>Engagement 项目包</Text> 与 <Text code>manifest.json</Text>{" "}
                建立关联，而非逐个孤立上传；报价任务完成后亦可归档回知识库。Demo 阶段仅对{" "}
                <Text strong>.docx</Text> 稳定索引，Excel / PDF 与页面上传项目包为 Phase 2。
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
                {`knowledge_base/<项目名>/
  ├── manifest.json    ← Phase 2：声明 RFQ / QA / 报价等关联
  ├── rfq.docx
  ├── qa.xlsx
  └── quote.xlsx`}
              </Paragraph>
            </>
          ),
        },
      ]}
    />
  );
}
