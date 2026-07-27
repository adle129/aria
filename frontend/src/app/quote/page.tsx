"use client";

import {
  Alert,
  Button,
  Card,
  Checkbox,
  Descriptions,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { DownloadOutlined, FileExcelOutlined } from "@ant-design/icons";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { apiClient, buildApiUrl } from "@/api/client";
import DemoModuleCapability from "@/components/DemoModuleCapability";
import MilestoneStepScaffold from "@/components/MilestoneStepScaffold";
import { useTaskContext } from "@/context/TaskContext";
import { useUiProfile } from "@/hooks/useUiProfile";
import {
  buildFunctionSourceSummaryRows,
  coalesceFunctionSourceMap,
  collectSourceCandidates,
  countMappedInScope,
  resolveInScopeFunctions,
} from "@/lib/functionSourceMap";
import { showsMilestoneScaffold } from "@/lib/uiProfile";
import type { ManpowerBreakdownItem } from "@/types/task";

const { Paragraph, Text, Title } = Typography;

interface GenerateResult {
  filename: string;
  download_url: string;
  manpower_plan?: {
    confidence?: string;
    baseline_sources?: string[];
    manpower_plan?: { PM?: unknown[]; Chassis?: unknown[] };
  };
}

function QuotePageContent() {
  const { profile } = useUiProfile();
  const searchParams = useSearchParams();
  const { taskId, task, loading, loadTask, setTaskId, syncFromPayload } = useTaskContext();
  const [generating, setGenerating] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [generateResult, setGenerateResult] = useState<GenerateResult | null>(null);
  const [breakdown, setBreakdown] = useState<ManpowerBreakdownItem[]>([]);
  const [breakdownLoading, setBreakdownLoading] = useState(false);
  const scaffoldOnly = showsMilestoneScaffold(profile, "quote");

  const loadBreakdown = useCallback(async (id: string) => {
    setBreakdownLoading(true);
    try {
      const resp = await apiClient.get<{
        code: number;
        data: { items: ManpowerBreakdownItem[]; demo_preview?: boolean };
      }>(`/rfq/tasks/${id}/manpower-breakdown-preview`, { silentError: true });
      setBreakdown(resp.data.data.items || []);
    } catch {
      setBreakdown([]);
    } finally {
      setBreakdownLoading(false);
    }
  }, []);

  useEffect(() => {
    const fromUrl = searchParams.get("task_id")?.trim();
    if (fromUrl) {
      setTaskId(fromUrl);
      if (scaffoldOnly) return;
      void loadTask(fromUrl).then((payload) => {
        if (payload) void loadBreakdown(fromUrl);
      });
    }
  }, [searchParams, loadTask, setTaskId, loadBreakdown, scaffoldOnly]);

  useEffect(() => {
    if (scaffoldOnly || !task?.task_id) return;
    void loadBreakdown(task.task_id);
  }, [task?.task_id, loadBreakdown, scaffoldOnly]);

  if (scaffoldOnly) {
    return <MilestoneStepScaffold step="quote" />;
  }

  const handleGenerate = async () => {
    const id = taskId.trim();
    if (!id || !confirmed) {
      message.warning("请勾选导出确认后再生成");
      return;
    }
    setGenerating(true);
    try {
      if (task?.status === "draft") {
        await apiClient.put(`/rfq/tasks/${id}`, { confirmed: true });
      }
      const resp = await apiClient.post<{ code: number; data: GenerateResult }>(
        `/rfq/tasks/${id}/generate-excel`,
      );
      setGenerateResult(resp.data.data);
      const refreshed = await loadTask(id);
      if (refreshed) syncFromPayload(refreshed);
      message.success("Excel 人力报价已生成");
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = () => {
    const id = taskId.trim();
    if (!id) return;
    window.open(buildApiUrl(`/rfq/tasks/${id}/download/excel`), "_blank");
  };

  const canGenerate =
    task?.processing_status === "completed" &&
    (task.status === "in_review" || task.status === "approved" || task.status === "exported" || confirmed);

  const projects =
    (task?.comparison_table as { projects?: Array<Record<string, unknown>> } | undefined)
      ?.projects || [];
  const inScopeFunctions = resolveInScopeFunctions(
    task?.rfq_modules as Record<string, unknown> | undefined,
  );
  const sourceCandidates = collectSourceCandidates(projects, task?.similar_projects);
  const sourceMap = coalesceFunctionSourceMap(
    task?.function_source_map,
    inScopeFunctions,
    null,
  );
  const sourceSummaryRows = buildFunctionSourceSummaryRows(
    sourceMap,
    inScopeFunctions,
    sourceCandidates,
  );
  const { mapped: mappedSourceCount, total: inScopeSourceTotal } = countMappedInScope(
    sourceMap,
    inScopeFunctions,
  );

  return (
    <div>
      <Title level={3}>人力报价</Title>
      <Paragraph type="secondary">
        报价助手 · 按 EDAG 模板生成 Excel 人力报价初稿（Demo：PM + Chassis 真实填充；人天分解为 Demo 预览）。
      </Paragraph>

      <DemoModuleCapability module="quote" />

      {!taskId && (
        <Alert
          type="info"
          showIcon
          message="请先在上方任务栏加载 RFQ 任务"
          style={{ marginBottom: 24 }}
        />
      )}

      <Spin spinning={loading}>
        {task && (
          <Card title="任务概览" style={{ marginBottom: 24 }}>
            <Descriptions column={2} size="small">
              <Descriptions.Item label="Task ID">
                <Text copyable={{ text: task.task_id }}>{task.task_id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="文件">{task.file_name}</Descriptions.Item>
              <Descriptions.Item label="分析状态">{task.processing_status}</Descriptions.Item>
              <Descriptions.Item label="审阅状态">{task.status}</Descriptions.Item>
              <Descriptions.Item label="项目">
                {String(task.rfq_modules?.project_name || "-")}
              </Descriptions.Item>
              <Descriptions.Item label="置信度">
                {String((task.comparison_table as { overall_confidence?: string })?.overall_confidence || "-")}
              </Descriptions.Item>
            </Descriptions>
            <Space style={{ marginTop: 12 }}>
              <Link href={`/rfq?task_id=${task.task_id}`}>返回 RFQ 分析</Link>
              <Link href={`/proposal?task_id=${task.task_id}`}>方案草案</Link>
              <Link href={`/qa?task_id=${task.task_id}`}>QA 清单</Link>
            </Space>
          </Card>
        )}
      </Spin>

      {task && task.processing_status === "completed" && (
        <Card
          title={
            <Space>
              <span>报价数据源（只读）</span>
              <Tag>
                已选用 {mappedSourceCount}/{inScopeSourceTotal}
              </Tag>
            </Space>
          }
          style={{ marginBottom: 24 }}
          extra={
            <Link href={`/rfq?task_id=${task.task_id}`}>在 RFQ 分析修改选源</Link>
          }
        >
          <Paragraph type="secondary" style={{ marginBottom: 12 }}>
            以下为 RFQ 页已保存的模块选源意向。本页不可改选；按多源真正拼装 Excel 属后续里程碑。
          </Paragraph>
          <Table
            size="small"
            pagination={false}
            rowKey="key"
            dataSource={sourceSummaryRows}
            columns={[
              { title: "报价模块", dataIndex: "moduleLabel", width: 140 },
              {
                title: "历史项目来源",
                dataIndex: "sourceLabel",
                render: (label: string, row) =>
                  row.inScope ? (
                    label
                  ) : (
                    <Text type="secondary">{label}</Text>
                  ),
              },
            ]}
          />
        </Card>
      )}

      {breakdown.length > 0 && (
        <Card
          title={
            <Space>
              <span>交付物级人天分解（Demo 预览）</span>
              <Tag color="orange">Demo 预览</Tag>
            </Space>
          }
          style={{ marginBottom: 24 }}
          loading={breakdownLoading}
        >
          <Table
            rowKey={(_, i) => String(i)}
            size="small"
            pagination={false}
            dataSource={breakdown}
            columns={[
              { title: "交付物", dataIndex: "deliverable" },
              { title: "Function", dataIndex: "function", width: 100 },
              { title: "人天", dataIndex: "man_days", width: 80 },
              { title: "来源", dataIndex: "source", width: 120 },
            ]}
          />
        </Card>
      )}

      <Card title="导出确认" style={{ marginBottom: 24 }}>
        <Checkbox checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)}>
          我已审阅 AI 生成内容与对比矩阵，确认可导出 Excel 人力明细（仅内部使用）
        </Checkbox>
        <div style={{ marginTop: 16 }}>
          <Space>
            <Button
              type="primary"
              icon={<FileExcelOutlined />}
              disabled={!task || !canGenerate}
              loading={generating}
              onClick={handleGenerate}
            >
              生成 Excel 报价初稿
            </Button>
            <Button
              icon={<DownloadOutlined />}
              disabled={!task?.excel_ready && !generateResult}
              onClick={handleDownload}
            >
              下载 Excel
            </Button>
          </Space>
        </div>
        {task?.status === "draft" && !confirmed && (
          <Alert
            style={{ marginTop: 16 }}
            type="warning"
            showIcon
            message="请先在 RFQ 页确认对比表，或勾选上方确认框后再生成"
          />
        )}
        {generateResult && (
          <Alert
            style={{ marginTop: 16 }}
            type="success"
            showIcon
            message={`已生成：${generateResult.filename}`}
            description={
              <Text type="secondary">
                基线来源：{(generateResult.manpower_plan?.baseline_sources || []).join("、") || "Mock 基线"}
              </Text>
            }
          />
        )}
      </Card>
    </div>
  );
}

export default function QuotePage() {
  return (
    <Suspense fallback={<Spin tip="加载中..." />}>
      <QuotePageContent />
    </Suspense>
  );
}
