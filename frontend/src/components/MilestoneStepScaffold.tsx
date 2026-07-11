"use client";

import { DownloadOutlined, FileExcelOutlined, FilePptOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Space, Table, Tag, Typography } from "antd";
import Link from "next/link";
import { MILESTONE_SCAFFOLD, type MilestoneScaffoldStep } from "@/lib/milestoneScaffold";

const { Paragraph, Text, Title } = Typography;

const PLACEHOLDER_ROWS = [
  { key: "1", col1: "—", col2: "—", col3: "—" },
  { key: "2", col1: "—", col2: "—", col3: "—" },
  { key: "3", col1: "—", col2: "—", col3: "—" },
];

function WireframeActions({ step }: { step: MilestoneScaffoldStep }) {
  if (step === "quote") {
    return (
      <Space wrap>
        <Button type="primary" disabled icon={<FileExcelOutlined />}>
          生成报价 Excel
        </Button>
        <Button disabled icon={<DownloadOutlined />}>
          下载 Excel
        </Button>
      </Space>
    );
  }
  if (step === "qa") {
    return (
      <Space wrap>
        <Button type="primary" disabled>
          生成 QA 清单
        </Button>
        <Button disabled icon={<DownloadOutlined />}>
          下载 Q_A Excel
        </Button>
      </Space>
    );
  }
  return (
    <Space wrap>
      <Button type="primary" disabled icon={<FilePptOutlined />}>
        生成方案 PPT
      </Button>
      <Button disabled icon={<DownloadOutlined />}>
        下载 PPT
      </Button>
    </Space>
  );
}

function WireframeTable({ step }: { step: MilestoneScaffoldStep }) {
  if (step === "quote") {
    return (
      <Table
        rowKey="key"
        size="small"
        pagination={false}
        dataSource={PLACEHOLDER_ROWS}
        columns={[
          { title: "Function", dataIndex: "col1", width: 120 },
          { title: "月列人天", dataIndex: "col2" },
          { title: "基线来源", dataIndex: "col3" },
        ]}
      />
    );
  }
  if (step === "qa") {
    return (
      <Table
        rowKey="key"
        size="small"
        pagination={false}
        dataSource={PLACEHOLDER_ROWS}
        columns={[
          { title: "Area", dataIndex: "col1", width: 100 },
          { title: "Question", dataIndex: "col2" },
          { title: "影响", dataIndex: "col3", width: 80 },
        ]}
      />
    );
  }
  return (
    <Table
      rowKey="key"
      size="small"
      pagination={false}
      dataSource={PLACEHOLDER_ROWS}
      columns={[
        { title: "Function", dataIndex: "col1", width: 100 },
        { title: "模块", dataIndex: "col2" },
        { title: "交付物", dataIndex: "col3" },
      ]}
    />
  );
}

export default function MilestoneStepScaffold({ step }: { step: MilestoneScaffoldStep }) {
  const content = MILESTONE_SCAFFOLD[step];

  return (
    <div>
      <Space align="center" wrap style={{ marginBottom: 8 }}>
        <Title level={3} style={{ margin: 0 }}>
          {content.title}
        </Title>
        <Tag color="default">待开通 · {content.milestone}</Tag>
        <Tag>路线图预览</Tag>
      </Space>
      <Paragraph type="secondary">{content.subtitle}</Paragraph>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
        message={`${content.milestone} 里程碑开通后可用`}
        description={
          <>
            当前为交付界面预览，不调用后端生成接口。请先完成{" "}
            <Link href="/rfq">RFQ 分析</Link> 与知识库对标（R1）；{content.milestone}{" "}
            验收后将替换为真实业务逻辑。
          </>
        }
      />

      <Card title={content.wireframeHint} style={{ marginBottom: 24 }}>
        <WireframeActions step={step} />
        <Paragraph type="secondary" style={{ marginTop: 16, marginBottom: 0, fontSize: 12 }}>
          上方按钮为界面占位，{content.milestone} 开通前不可操作。
        </Paragraph>
      </Card>

      <Card title="本阶段交付物" style={{ marginBottom: 24 }}>
        <ul style={{ margin: 0, paddingLeft: 20 }}>
          {content.deliverables.map((item) => (
            <li key={item} style={{ marginBottom: 6 }}>
              <Text>{item}</Text>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="界面结构预览" extra={<Text type="secondary">示意 · 无真实数据</Text>}>
        <WireframeTable step={step} />
      </Card>
    </div>
  );
}
