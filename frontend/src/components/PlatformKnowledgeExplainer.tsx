"use client";

import { Collapse, Space, Table, Tag, Typography } from "antd";
import { useUiProfile } from "@/hooks/useUiProfile";
import {
  DEMO_ENGINEER_USAGE_ROWS,
  ENGINEER_FOOTER,
  ENGINEER_INTRO,
  ENGINEER_USAGE_ROWS,
} from "@/lib/platformKnowledgeCopy";

const { Paragraph, Text } = Typography;

type AdminConsumerRow = {
  key: string;
  consumer: string;
  status: string;
  statusColor: "processing" | "default" | "success";
  detail: string;
};

type AdminStageRow = {
  key: string;
  stage: string;
  usage: string;
  docTypes: string;
};

const ADMIN_CONSUMER_ROWS_DEMO: AdminConsumerRow[] = [
  {
    key: "quoting",
    consumer: "报价助手",
    status: "当前可用",
    statusColor: "processing",
    detail: "RFQ 对标与相似项目检索；方案 / 问答等能力后续接入",
  },
  {
    key: "future",
    consumer: "更多应用",
    status: "规划中",
    statusColor: "default",
    detail: "共用同一套历史资料库，按角色控制查看与维护权限",
  },
];

const ADMIN_CONSUMER_ROWS_R1: AdminConsumerRow[] = [
  {
    key: "quoting",
    consumer: "报价助手",
    status: "当前可用",
    statusColor: "success",
    detail: "RFQ 技术对标与历史项目检索；方案 / 问答 / Excel 报价按合同阶段陆续开放",
  },
  {
    key: "future",
    consumer: "更多应用",
    status: "规划中",
    statusColor: "default",
    detail: "共用同一套历史资料库，按角色控制查看与维护权限",
  },
];

const ADMIN_STAGE_ROWS_DEMO: AdminStageRow[] = [
  {
    key: "rfq",
    stage: "RFQ 分析",
    usage: "相似项目、对比矩阵、领域缺口提示",
    docTypes: "RFQ、方案摘要",
  },
  {
    key: "qa",
    stage: "问答清单",
    usage: "历史问题与参考依据",
    docTypes: "问答清单",
  },
  {
    key: "quote",
    stage: "人力报价",
    usage: "历史人天与岗位配置参考",
    docTypes: "人力报价",
  },
];

const ADMIN_STAGE_ROWS_R1: AdminStageRow[] = [
  {
    key: "rfq",
    stage: "RFQ 分析",
    usage: "相似项目、对比矩阵、维度确认、人天基线参考",
    docTypes: "RFQ、问答清单",
  },
  {
    key: "baselines",
    stage: "人天基线",
    usage: "从历史报价表提取人天，可对照源表",
    docTypes: "人力报价",
  },
];

function EngineerExplainer({ showDemoChrome }: { showDemoChrome: boolean }) {
  const rows = showDemoChrome ? DEMO_ENGINEER_USAGE_ROWS : ENGINEER_USAGE_ROWS;
  return (
    <>
      <Paragraph type="secondary" style={{ marginTop: 0 }}>
        {ENGINEER_INTRO}
      </Paragraph>

      <Text strong>和报价工作的关系</Text>
      <Table
        size="small"
        pagination={false}
        style={{ marginTop: 8, marginBottom: 12 }}
        rowKey="key"
        dataSource={rows}
        columns={[
          { title: "你在做什么", dataIndex: "stage", width: 120 },
          { title: "本库如何帮助你", dataIndex: "help" },
        ]}
      />

      <Paragraph type="secondary" style={{ marginBottom: 0 }}>
        {ENGINEER_FOOTER}
      </Paragraph>
    </>
  );
}

function AdminExplainer({ showDemoChrome }: { showDemoChrome: boolean }) {
  const consumerRows = showDemoChrome ? ADMIN_CONSUMER_ROWS_DEMO : ADMIN_CONSUMER_ROWS_R1;
  const stageRows = showDemoChrome ? ADMIN_STAGE_ROWS_DEMO : ADMIN_STAGE_ROWS_R1;

  return (
    <>
      <Paragraph type="secondary" style={{ marginTop: 0 }}>
        本页管理 ARIA <Text strong>平台知识库</Text>
        （历史项目 RFQ、问答清单、人力报价等）。报价工程师在「RFQ 分析」完成对标；你在此完成项目资料入库、更新检索索引，并做检索验证。
      </Paragraph>

      <Table
        size="small"
        pagination={false}
        style={{ marginBottom: 16 }}
        rowKey="key"
        dataSource={consumerRows}
        columns={[
          { title: "使用方", dataIndex: "consumer", width: 120 },
          {
            title: "状态",
            dataIndex: "status",
            width: 100,
            render: (v: string, row) => <Tag color={row.statusColor}>{v}</Tag>,
          },
          { title: "说明", dataIndex: "detail" },
        ]}
      />

      <Text strong>报价助手如何用到本库</Text>
      <Table
        size="small"
        pagination={false}
        style={{ marginTop: 8, marginBottom: 16 }}
        rowKey="key"
        dataSource={stageRows}
        columns={[
          { title: "报价环节", dataIndex: "stage", width: 100 },
          { title: "用途", dataIndex: "usage" },
          { title: "资料类型", dataIndex: "docTypes", width: 140 },
        ]}
      />

      <Text strong>项目资料包</Text>
      <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 8 }}>
        一套完整项目通常包含 RFQ、问答清单、人力报价 Excel。用项目目录与清单文件关联后：RFQ
        与问答可供相似检索，报价表解析为人天基线。
        {showDemoChrome
          ? " Demo 环境部分能力为占位；正式环境支持本页上传与 IT 目录批量入库。"
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
        {`knowledge_base/<项目目录>/
  ├── manifest.json
  ├── RFQ_xxx.docx
  ├── Q_A_xxx.xlsx
  └── Quote_xxx.xlsx`}
      </Paragraph>
    </>
  );
}

export default function PlatformKnowledgeExplainer({
  canWriteKb = true,
}: {
  canWriteKb?: boolean;
}) {
  const { showDemoChrome } = useUiProfile();

  return (
    <Collapse
      defaultActiveKey={canWriteKb ? (showDemoChrome ? ["platform"] : []) : ["platform"]}
      style={{ marginBottom: 16 }}
      items={[
        {
          key: "platform",
          label: canWriteKb ? (
            <Space>
              <Text strong>平台说明</Text>
              <Tag color="blue">管理指南</Tag>
              <Text type="secondary">入库与资料结构</Text>
            </Space>
          ) : (
            <Space>
              <Text strong>本库说明</Text>
              <Text type="secondary">如何帮助报价分析</Text>
            </Space>
          ),
          children: canWriteKb ? (
            <AdminExplainer showDemoChrome={showDemoChrome} />
          ) : (
            <EngineerExplainer showDemoChrome={showDemoChrome} />
          ),
        },
      ]}
    />
  );
}
