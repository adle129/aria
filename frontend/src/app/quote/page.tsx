"use client";

import { Alert, Card, Checkbox, Typography } from "antd";

const { Paragraph, Title } = Typography;

export default function QuotePage() {
  return (
    <div>
      <Title level={3}>人力报价</Title>
      <Paragraph type="secondary">
        基于 RFQ 解析结果与历史基线，按 EDAG 模板生成 Excel 人力报价初稿。
      </Paragraph>
      <Alert
        message="Phase 0 脚手架"
        description="Excel 生成功能将在 ExcelManpowerGenerator 模块完成后接入。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />
      <Card title="导出确认">
        <Checkbox disabled>我已审阅 AI 生成内容，确认可导出</Checkbox>
      </Card>
    </div>
  );
}
