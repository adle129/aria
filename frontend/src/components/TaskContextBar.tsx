"use client";

import { useEffect, useState } from "react";
import { Button, Space, Tag, Typography } from "antd";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { apiClient } from "@/api/client";
import { useTaskContext } from "@/context/TaskContext";
import WorkflowSteps from "@/components/WorkflowSteps";
import {
  contextBarOpenLabel,
  formatContextBarHeadline,
  formatContextBarQueueHint,
  formatContextBarTagLabel,
  shouldPollContextBarStatus,
} from "@/lib/taskContextBarCopy";
import { getProcessingStatusTagStyle } from "@/lib/taskStatus";
import { isTaskContextBarVisible } from "@/lib/uiProfile";

const { Text } = Typography;

const STATUS_POLL_MS = 5000;

export default function TaskContextBar() {
  const pathname = usePathname();
  const { task, loading } = useTaskContext();
  const [queuePosition, setQueuePosition] = useState<number | null>(null);
  const [estimatedWaitSeconds, setEstimatedWaitSeconds] = useState<number | null>(null);
  const [liveStatus, setLiveStatus] = useState<string | null>(null);

  const processingStatus = liveStatus || task?.processing_status || "";
  // Bar is hidden on /rfq and platform pages — never poll status there.
  const barVisible =
    isTaskContextBarVisible(pathname) && !pathname.startsWith("/rfq");

  useEffect(() => {
    setLiveStatus(null);
    setQueuePosition(null);
    setEstimatedWaitSeconds(null);
  }, [task?.task_id]);

  useEffect(() => {
    if (!barVisible || !task?.task_id) return;
    if (!shouldPollContextBarStatus(task.processing_status)) {
      return;
    }

    let cancelled = false;
    let timer: number | undefined;

    const pull = async () => {
      try {
        const resp = await apiClient.get<{
          status: string;
          queue_position?: number | null;
          estimated_wait_seconds?: number | null;
        }>(`/rfq/tasks/${task.task_id}/status`, { silentError: true });
        if (cancelled) return;
        setLiveStatus(resp.data.status);
        setQueuePosition(resp.data.queue_position ?? null);
        setEstimatedWaitSeconds(resp.data.estimated_wait_seconds ?? null);
        if (!shouldPollContextBarStatus(resp.data.status) && timer != null) {
          window.clearInterval(timer);
          timer = undefined;
        }
      } catch {
        // best-effort; keep last known task payload
      }
    };

    void pull();
    timer = window.setInterval(() => void pull(), STATUS_POLL_MS);
    return () => {
      cancelled = true;
      if (timer != null) window.clearInterval(timer);
    };
  }, [barVisible, task?.task_id, task?.processing_status]);

  if (!barVisible) return null;

  const tagStyle = getProcessingStatusTagStyle(processingStatus || "pending");
  const headline = task
    ? formatContextBarHeadline({
        fileName: task.file_name,
        processingStatus,
        queuePosition,
      })
    : null;
  const queueHint = task
    ? formatContextBarQueueHint({
        processingStatus,
        queuePosition,
        estimatedWaitSeconds,
      })
    : null;

  return (
    <div
      style={{ marginBottom: 24, paddingBottom: 16, borderBottom: "1px solid #F0F0F0" }}
      data-testid="task-context-bar"
    >
      <WorkflowSteps status={task?.artifacts_status} currentPath={pathname} />
      {task ? (
        <Space direction="vertical" size={6} style={{ marginTop: 12, width: "100%" }}>
          <Space wrap size={8}>
            <Text strong data-testid="task-context-bar-headline">
              {headline}
            </Text>
            <Tag
              style={{
                color: tagStyle.color,
                background: tagStyle.background,
                borderColor: tagStyle.borderColor,
                margin: 0,
                fontWeight: 500,
              }}
              data-testid="task-context-bar-tag"
            >
              {formatContextBarTagLabel(processingStatus)}
            </Tag>
            <Link href={`/rfq?task_id=${task.task_id}`}>
              <Button type="link" size="small" loading={loading} style={{ paddingInline: 0 }}>
                {contextBarOpenLabel(processingStatus)}
              </Button>
            </Link>
          </Space>
          {queueHint && (
            <Text type="secondary" style={{ fontSize: 12 }} data-testid="task-context-bar-queue">
              {queueHint}
            </Text>
          )}
        </Space>
      ) : (
        <Text type="secondary" style={{ display: "block", marginTop: 12 }}>
          尚未加载任务 · <Link href="/rfq">前往 RFQ 分析上传或选择任务</Link>
        </Text>
      )}
    </div>
  );
}
