"use client";

import { CopyOutlined, UploadOutlined } from "@ant-design/icons";
import { Button, Space, Typography, message } from "antd";
import RfqStatusTag from "@/components/rfq/RfqStatusTag";
import { copyToClipboard, formatTaskShortId } from "@/lib/clipboard";
import { formatTaskTimingLine } from "@/lib/formatDuration";
import type { TaskPayload } from "@/types/task";

const { Title, Text } = Typography;

const SHOW_TIMING_STATUSES = new Set([
  "dimension_review",
  "completed",
  "failed",
  "cancelled",
  "retrieving",
  "generating",
]);

interface RfqTaskHeaderProps {
  task: TaskPayload;
  onUploadNew: () => void;
}

export default function RfqTaskHeader({ task, onUploadNew }: RfqTaskHeaderProps) {
  const mods = task.rfq_modules as Record<string, unknown> | undefined;
  const project = mods?.project_name ? String(mods.project_name) : "";
  const customer = mods?.customer ? String(mods.customer) : "";
  const platform = mods?.platform_type ? String(mods.platform_type) : "";
  const months = mods?.timeline_months != null ? `${mods.timeline_months} 个月` : "";
  const subtitle = [project, customer, platform, months].filter(Boolean).join(" · ");
  const shortId = formatTaskShortId(task.task_id);
  const timingLine = SHOW_TIMING_STATUSES.has(task.processing_status)
    ? formatTaskTimingLine({
        queueWaitMs: task.queue_wait_ms,
        runMs: task.run_ms,
      })
    : null;

  const handleCopyTaskId = () => {
    void copyToClipboard(task.task_id)
      .then(() => message.success(`任务编号 #${shortId} 已复制`))
      .catch(() => message.error("复制失败，请手动选择编号"));
  };

  return (
    <div style={{ marginBottom: 24 }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div style={{ minWidth: 0, flex: 1 }}>
          <Space wrap align="center" size={10} style={{ marginBottom: 6 }}>
            <Title level={4} style={{ margin: 0, fontWeight: 600, letterSpacing: -0.2 }}>
              {task.file_name || "RFQ 任务"}
            </Title>
            <RfqStatusTag
              processingStatus={task.processing_status}
              statusMessage={task.status_message}
            />
          </Space>
          <Text type="secondary" style={{ fontSize: 13, lineHeight: 1.5, display: "block" }}>
            {subtitle || "项目与客户信息解析后将显示于此"}
          </Text>
          {timingLine ? (
            <Text
              type="secondary"
              style={{ fontSize: 12, display: "block", marginTop: 4 }}
              data-testid="rfq-task-timing"
            >
              {timingLine}
            </Text>
          ) : null}
          <Button
            type="link"
            size="small"
            icon={<CopyOutlined />}
            onClick={handleCopyTaskId}
            style={{ paddingInline: 0, height: "auto", fontSize: 12, marginTop: 2 }}
          >
            任务编号 #{shortId}
          </Button>
        </div>
        <Space size={4}>
          <Button type="text" size="small" icon={<UploadOutlined />} onClick={onUploadNew}>
            上传新 RFQ
          </Button>
        </Space>
      </div>
    </div>
  );
}
