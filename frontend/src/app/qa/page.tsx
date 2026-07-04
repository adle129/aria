"use client";

import {
  Alert,
  Button,
  Card,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { apiClient, buildApiUrl } from "@/api/client";
import DemoModuleCapability from "@/components/DemoModuleCapability";
import { useTaskContext } from "@/context/TaskContext";
import type { QAItem, TaskPayload } from "@/types/task";

const { Paragraph, Title } = Typography;

const IMPACT_COLOR: Record<string, string> = {
  高: "red",
  中: "orange",
  低: "default",
};

function displayFunction(row: QAItem): string {
  return row.function || row.area || "—";
}

export default function QAPage() {
  return (
    <Suspense fallback={<Spin tip="加载中..." />}>
      <QAPageContent />
    </Suspense>
  );
}

function QAPageContent() {
  const searchParams = useSearchParams();
  const { taskId, task, loading, loadTask, setTaskId, syncFromPayload } = useTaskContext();
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    const fromUrl = searchParams.get("task_id")?.trim();
    if (fromUrl) {
      setTaskId(fromUrl);
      void loadTask(fromUrl);
    }
  }, [searchParams, loadTask, setTaskId]);

  const items = task?.qa_items || [];
  const rfqReady = task?.processing_status === "completed";
  const canDownload = rfqReady;

  const handleGenerate = async () => {
    const id = taskId.trim();
    if (!id) {
      message.warning("请先加载 RFQ 任务");
      return;
    }
    setGenerating(true);
    try {
      const resp = await apiClient.post<{
        code: number;
        data: {
          demo_preview?: boolean;
          filename?: string;
          download_url?: string;
          task: TaskPayload;
        };
      }>(`/rfq/tasks/${id}/generate-qa`);
      syncFromPayload(resp.data.data.task);
      message.success(
        resp.data.data.filename
          ? `已加载 Mock 示例，可下载 ${resp.data.data.filename}`
          : "已加载 Mock 示例数据",
      );
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = () => {
    const id = taskId.trim();
    if (!id) return;
    window.open(buildApiUrl(`/rfq/tasks/${id}/download/qa`), "_blank");
  };

  return (
    <div>
      <Title level={3}>QA 清单</Title>
      <Paragraph type="secondary">
        报价助手 · 待澄清技术问题清单（Demo 预览；Phase 2 基于历史 Q_A 真实生成）。
      </Paragraph>

      <DemoModuleCapability module="qa" />

      {!taskId && (
        <Alert
          type="info"
          showIcon
          message="尚未选择任务"
          description="请先在上方任务栏选择历史分析，或在 RFQ 页上传并完成分析。"
          style={{ marginBottom: 24 }}
        />
      )}

      <Card title="QA 清单" style={{ marginBottom: 24 }}>
        <Space wrap>
          <Button
            icon={<DownloadOutlined />}
            type="primary"
            disabled={!canDownload}
            onClick={handleDownload}
          >
            下载 Q_A Excel
          </Button>
          <Button
            loading={generating || loading}
            disabled={!rfqReady}
            onClick={handleGenerate}
          >
            加载 Mock 示例清单
          </Button>
          <Button onClick={() => void loadTask()} loading={loading}>
            刷新任务
          </Button>
          {task?.artifacts_status?.qa_ready && (
            <Link href={`/quote?task_id=${taskId}`}>
              <Button>前往人力报价</Button>
            </Link>
          )}
        </Space>
        {!rfqReady && taskId && (
          <Alert
            style={{ marginTop: 16 }}
            type="warning"
            showIcon
            message="RFQ 分析完成后可下载 Q_A Excel"
          />
        )}
      </Card>

      {items.length > 0 ? (
        <Card
          title={`待澄清问题（${items.length} 条）`}
          extra={<Tag color="orange">Demo 预览</Tag>}
        >
          <Table
            rowKey="no"
            size="small"
            pagination={false}
            dataSource={items}
            columns={[
              { title: "序号", dataIndex: "no", width: 64 },
              { title: "待澄清问题", dataIndex: "question" },
              {
                title: "涉及功能",
                width: 140,
                render: (_: unknown, row: QAItem) => displayFunction(row),
              },
              {
                title: "影响程度",
                dataIndex: "impact",
                width: 96,
                render: (v: string) => <Tag color={IMPACT_COLOR[v] || "default"}>{v}</Tag>,
              },
              {
                title: "历史依据",
                dataIndex: "history_reference",
                render: (v: string) => v || "—",
              },
            ]}
          />
        </Card>
      ) : (
        rfqReady && (
          <Alert
            type="info"
            showIcon
            message="可直接下载仅含表头的 Q_A Excel，或点击「加载 Mock 示例清单」查看界面示例"
          />
        )
      )}
    </div>
  );
}
