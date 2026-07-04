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
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { apiClient } from "@/api/client";
import DemoModuleCapability from "@/components/DemoModuleCapability";
import { useTaskContext } from "@/context/TaskContext";
import type { SolutionDraftSection, TaskPayload } from "@/types/task";

const { Paragraph, Title, Text } = Typography;

export default function ProposalPage() {
  return (
    <Suspense fallback={<Spin tip="加载中..." />}>
      <ProposalPageContent />
    </Suspense>
  );
}

function ProposalPageContent() {
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

  const sections = task?.solution_draft?.sections || [];
  const canGenerate = task?.processing_status === "completed";

  const handleGenerate = async () => {
    const id = taskId.trim();
    if (!id) {
      message.warning("请先加载 RFQ 任务");
      return;
    }
    setGenerating(true);
    try {
      const resp = await apiClient.post<{ code: number; data: { demo_preview?: boolean; task: TaskPayload } }>(
        `/rfq/tasks/${id}/generate-proposal`,
      );
      syncFromPayload(resp.data.data.task);
      message.success("已加载 Mock 方案示例");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div>
      <Title level={3}>方案草案</Title>
      <Paragraph type="secondary">
        报价助手 · 预览技术方案模块结构（Demo 预览；Phase 2 接入真实 RAG + LLM）。
      </Paragraph>

      <DemoModuleCapability module="proposal" />

      {!taskId && (
        <Alert
          type="info"
          showIcon
          message="尚未选择任务"
          description="请先在上方任务栏选择历史分析，或在 RFQ 页上传并完成分析。"
          style={{ marginBottom: 24 }}
        />
      )}

      <Card title="生成方案" style={{ marginBottom: 24 }}>
        <Space wrap>
          <Button
            type="primary"
            loading={generating || loading}
            disabled={!canGenerate}
            onClick={handleGenerate}
          >
            加载 Mock 方案示例
          </Button>
          <Button onClick={() => void loadTask()} loading={loading}>
            刷新任务
          </Button>
          {task?.artifacts_status?.proposal_ready && (
            <Link href={`/qa?task_id=${taskId}`}>
              <Button>前往 QA 清单</Button>
            </Link>
          )}
        </Space>
        {!canGenerate && taskId && task && task.processing_status !== "completed" && (
          <Alert
            style={{ marginTop: 16 }}
            type="warning"
            showIcon
            message="RFQ 分析尚未完成，请等待解析结束后再生成"
          />
        )}
        {task?.solution_draft && (
          <Alert
            style={{ marginTop: 16 }}
            type="warning"
            showIcon
            message="Demo 预览 · 下方为 Mock 示例，未调用大模型"
          />
        )}
      </Card>

      {sections.length > 0 ? (
        <Card
          title={`方案模块（${sections.length} 节）`}
          extra={<Tag color="orange">Demo 预览</Tag>}
        >
          <Table
            rowKey={(_, i) => String(i)}
            size="small"
            pagination={false}
            dataSource={sections}
            expandable={{
              expandedRowRender: (row: SolutionDraftSection) => (
                <div style={{ padding: "8px 0" }}>
                  <p>
                    <Text strong>假设：</Text>
                    {row.assumptions || "—"}
                  </p>
                  <p>
                    <Text strong>输入：</Text>
                    {row.inputs || "—"}
                  </p>
                  <p>
                    <Text strong>工作内容：</Text>
                    {row.work_content || "—"}
                  </p>
                  <p>
                    <Text strong>交付物：</Text>
                    {row.deliverables || "—"}
                  </p>
                  <p>
                    <Text strong>参考项目：</Text>
                    {row.source_project || "—"}
                    {row.deviation_rate ? ` · 偏差 ${row.deviation_rate}` : ""}
                    {row.similarity_score != null
                      ? ` · 相似度 ${Math.round(row.similarity_score * 100)}%`
                      : ""}
                  </p>
                </div>
              ),
            }}
            columns={[
              { title: "Function", dataIndex: "function", width: 100 },
              { title: "模块 Key", dataIndex: "module_key" },
              {
                title: "交付物",
                dataIndex: "deliverables",
                ellipsis: true,
              },
              { title: "参考项目", dataIndex: "source_project", ellipsis: true },
            ]}
          />
        </Card>
      ) : (
        task?.processing_status === "completed" && (
          <Alert type="info" showIcon message="尚未加载示例，点击「加载 Mock 方案示例」预览界面结构" />
        )
      )}
    </div>
  );
}
