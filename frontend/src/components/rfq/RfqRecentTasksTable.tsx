"use client";

import { CopyOutlined } from "@ant-design/icons";
import { Spin, Typography, message } from "antd";
import { copyToClipboard, formatTaskShortId } from "@/lib/clipboard";
import { formatRelativeTime } from "@/lib/taskStatus";
import RfqStatusTag from "@/components/rfq/RfqStatusTag";
import type { TaskSummary } from "@/types/task";

const { Text } = Typography;

interface RfqRecentTasksTableProps {
  tasks: TaskSummary[];
  activeTaskId?: string;
  loading?: boolean;
  onOpen: (taskId: string) => void;
}

function taskSubtitle(task: TaskSummary): string {
  return [task.project_name, task.customer].filter(Boolean).join(" · ");
}

export default function RfqRecentTasksTable({
  tasks,
  activeTaskId,
  loading,
  onOpen,
}: RfqRecentTasksTableProps) {
  if (loading && tasks.length === 0) {
    return (
      <div style={{ padding: 24, textAlign: "center" }}>
        <Spin size="small" />
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div style={{ padding: "20px 12px", textAlign: "center" }}>
        <Text type="secondary">暂无历史 RFQ</Text>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      {tasks.map((task) => {
        const active = task.task_id === activeTaskId;
        const subtitle = taskSubtitle(task);
        const shortId = formatTaskShortId(task.task_id);
        return (
          <button
            key={task.task_id}
            type="button"
            onClick={() => onOpen(task.task_id)}
            style={{
              display: "block",
              width: "100%",
              textAlign: "left",
              border: "none",
              borderBottom: "1px solid #F0F0F0",
              background: active ? "#FAFAFA" : "#FFFFFF",
              borderLeft: active ? "2px solid #E30613" : "2px solid transparent",
              padding: "10px 12px",
              cursor: "pointer",
              transition: "background 0.15s ease",
            }}
            onMouseEnter={(e) => {
              if (!active) e.currentTarget.style.background = "#F7F7F7";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = active ? "#FAFAFA" : "#FFFFFF";
            }}
          >
            <div
              style={{
                fontWeight: active ? 600 : 500,
                fontSize: 14,
                color: "#1A1A1A",
                lineHeight: 1.4,
                marginBottom: subtitle ? 2 : 6,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
              title={task.file_name}
            >
              {task.file_name}
            </div>
            {subtitle ? (
              <div
                style={{
                  fontSize: 11,
                  color: "#8C8C8C",
                  marginBottom: 6,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
                title={subtitle}
              >
                {subtitle}
              </div>
            ) : null}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 8,
              }}
            >
              <RfqStatusTag
                processingStatus={task.processing_status}
                statusMessage={task.status_message}
              />
              <span
                style={{ display: "flex", alignItems: "center", gap: 4, flexShrink: 0 }}
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  type="button"
                  title={`任务编号 #${shortId}，点击复制完整编号`}
                  onClick={() => {
                    void copyToClipboard(task.task_id)
                      .then(() => message.success(`任务编号 #${shortId} 已复制`))
                      .catch(() => message.error("复制失败"));
                  }}
                  style={{
                    border: "none",
                    background: "transparent",
                    padding: 0,
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 3,
                    fontSize: 11,
                    color: "#8C8C8C",
                  }}
                >
                  <span>#{shortId}</span>
                  <CopyOutlined style={{ fontSize: 10 }} />
                </button>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  · {formatRelativeTime(task.created_at)}
                </Text>
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
