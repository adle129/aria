"use client";

import { Button, Card, Input, Select, Space, Typography } from "antd";
import { usePathname } from "next/navigation";
import { useTaskContext } from "@/context/TaskContext";
import WorkflowSteps from "@/components/WorkflowSteps";

const { Text } = Typography;

function formatTaskLabel(t: { task_id: string; file_name: string; processing_status: string; created_at?: string }) {
  const shortId = t.task_id.slice(0, 8);
  const time = t.created_at
    ? new Date(t.created_at).toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      })
    : "";
  return `${t.file_name} · ${t.processing_status} · ${shortId}${time ? ` · ${time}` : ""}`;
}

export default function TaskContextBar() {
  const pathname = usePathname();
  const { taskId, task, loading, recentTasks, setTaskId, loadTask } = useTaskContext();

  if (pathname === "/" || pathname.startsWith("/knowledge")) return null;

  return (
    <Card size="small" style={{ marginBottom: 24 }} title="当前报价任务">
      <Space wrap style={{ width: "100%", marginBottom: 12 }}>
        <Select
          placeholder="从最近分析选择"
          style={{ width: 360 }}
          allowClear
          showSearch
          optionFilterProp="label"
          value={taskId || undefined}
          onChange={(value) => setTaskId(value || "")}
          options={recentTasks.map((t) => ({
            value: t.task_id,
            label: formatTaskLabel(t),
          }))}
        />
        <Input
          placeholder="或粘贴 task_id"
          value={taskId}
          onChange={(e) => setTaskId(e.target.value)}
          onPressEnter={() => void loadTask()}
          style={{ width: 280 }}
        />
        <Button type="primary" loading={loading} onClick={() => void loadTask()}>
          加载
        </Button>
        {task && (
          <Text type="secondary">
            {task.file_name || "—"} · {task.processing_status} · 审阅 {task.status}
          </Text>
        )}
      </Space>
      <WorkflowSteps status={task?.artifacts_status} currentPath={pathname} />
    </Card>
  );
}
