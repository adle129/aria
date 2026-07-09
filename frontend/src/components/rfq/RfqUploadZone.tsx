"use client";

import { InboxOutlined } from "@ant-design/icons";
import { Typography, Upload } from "antd";

const { Dragger } = Upload;
const { Paragraph, Text } = Typography;

interface RfqUploadZoneProps {
  disabled?: boolean;
  useRealLlm: boolean | null;
  showDemoChrome: boolean;
  onUpload: (file: File) => void;
}

export default function RfqUploadZone({
  disabled,
  useRealLlm,
  showDemoChrome,
  onUpload,
}: RfqUploadZoneProps) {
  return (
    <div style={{ maxWidth: 480, margin: "40px auto", padding: "8px 0 32px" }}>
      <Paragraph style={{ textAlign: "center", marginBottom: 20, fontSize: 15, color: "#333" }}>
        上传一份客户 RFQ，开始分析
      </Paragraph>
      <Dragger
        multiple={false}
        accept=".docx,.doc"
        showUploadList={false}
        disabled={disabled}
        style={{ padding: "16px 8px", background: "#FAFAFA", borderRadius: 8 }}
        beforeUpload={(file) => {
          onUpload(file as File);
          return false;
        }}
      >
        <p className="ant-upload-drag-icon" style={{ marginBottom: 8 }}>
          <InboxOutlined style={{ color: "#8C8C8C" }} />
        </p>
        <p className="ant-upload-text" style={{ fontSize: 14 }}>
          点击或拖拽 .docx / .doc 到此处
        </p>
        <p className="ant-upload-hint" style={{ fontSize: 12 }}>
          {useRealLlm === false && showDemoChrome
            ? "Mock 模式：规则提取；支持人工修订对比表"
            : useRealLlm
              ? "规则优先解析；维度确认后生成 Top-3 对标矩阵"
              : "上传后自动触发异步分析"}
        </p>
      </Dragger>
      <Paragraph type="secondary" style={{ textAlign: "center", marginTop: 16, marginBottom: 0, fontSize: 12 }}>
        <Text>也可从左侧「最近 RFQ」打开历史任务</Text>
      </Paragraph>
    </div>
  );
}
