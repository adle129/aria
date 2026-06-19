"use client";

import { Alert, Card, Typography, Upload } from "antd";
import { InboxOutlined } from "@ant-design/icons";

const { Dragger } = Upload;
const { Paragraph, Title } = Typography;

export default function RfqPage() {
  return (
    <div>
      <Title level={3}>RFQ 分析</Title>
      <Paragraph type="secondary">
        上传客户 RFQ 文档（.docx），系统将解析 Function 模块并检索相似历史项目。
      </Paragraph>
      <Alert
        message="Phase 0 脚手架"
        description="上传与解析功能将在下一阶段实现。当前可验证页面布局与后端 health 接口。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />
      <Card title="上传 RFQ">
        <Dragger disabled multiple={false} accept=".docx">
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽 .docx 文件到此区域</p>
          <p className="ant-upload-hint">即将支持：上传后自动触发异步分析任务</p>
        </Dragger>
      </Card>
    </div>
  );
}
