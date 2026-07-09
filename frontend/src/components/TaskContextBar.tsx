"use client";

import { Button, Space, Typography } from "antd";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTaskContext } from "@/context/TaskContext";
import RfqStatusTag from "@/components/rfq/RfqStatusTag";
import WorkflowSteps from "@/components/WorkflowSteps";
import { isTaskContextBarVisible } from "@/lib/uiProfile";

const { Text } = Typography;

export default function TaskContextBar() {
  const pathname = usePathname();
  const { task, loading } = useTaskContext();

  if (!isTaskContextBarVisible(pathname)) return null;

  if (pathname.startsWith("/rfq")) {
    return null;
  }

  return (
    <div style={{ marginBottom: 24, paddingBottom: 16, borderBottom: "1px solid #F0F0F0" }}>
      <WorkflowSteps status={task?.artifacts_status} currentPath={pathname} />
      {task ? (
        <Space wrap style={{ marginTop: 12 }} size={8}>
          <Text strong>{task.file_name || "—"}</Text>
          <RfqStatusTag
            processingStatus={task.processing_status}
            statusMessage={task.status_message}
          />
          <Link href={`/rfq?task_id=${task.task_id}`}>
            <Button type="link" size="small" loading={loading} style={{ paddingInline: 0 }}>
              在 RFQ 分析中打开
            </Button>
          </Link>
        </Space>
      ) : (
        <Text type="secondary" style={{ display: "block", marginTop: 12 }}>
          尚未加载任务 · <Link href="/rfq">前往 RFQ 分析上传或选择任务</Link>
        </Text>
      )}
    </div>
  );
}
