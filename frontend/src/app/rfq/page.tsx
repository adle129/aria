"use client";

import {
  Alert,
  Button,
  Card,
  Checkbox,
  Collapse,
  Descriptions,
  List,
  Progress,
  Space,
  Spin,
  Table,
  Typography,
  Upload,
  message,
} from "antd";
import { InboxOutlined } from "@ant-design/icons";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { apiClient, fetchHealth } from "@/api/client";
import { ComparisonMatrix, ConfidenceBadge, type MatrixRow } from "@/components/ComparisonMatrix";
import { useTaskContext } from "@/context/TaskContext";
import type { TaskPayload, TaskSummary } from "@/types/task";

const { Dragger } = Upload;
const { Paragraph, Title, Text } = Typography;

interface TaskData extends TaskPayload {}

interface TaskStatusPayload {
  status: string;
  progress: number;
  message: string;
}

const POLL_INTERVAL_MS = 500;
/** Mock ~30s; real LLM up to 120s × 3 attempts */
const POLL_MAX_ITERATIONS = 360;

const STAGE_LABELS: Record<string, string> = {
  pending: "等待处理",
  parsing: "正在解析 RFQ（LLM 可能需 1–2 分钟）",
  retrieving: "正在检索相似历史项目",
  generating: "正在生成技术维度对比表",
  completed: "分析完成",
  failed: "分析失败",
};

export default function RfqPage() {
  const { syncFromPayload, refreshRecentTasks, recentTasks, loadTask: loadTaskFromContext } =
    useTaskContext();
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [task, setTask] = useState<TaskData | null>(null);
  const [matrixRows, setMatrixRows] = useState<MatrixRow[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisMessage, setAnalysisMessage] = useState("");
  const [useRealLlm, setUseRealLlm] = useState<boolean | null>(null);
  const [restoring, setRestoring] = useState(true);

  useEffect(() => {
    fetchHealth()
      .then((h) => setUseRealLlm(!h.mock_llm))
      .catch(() => setUseRealLlm(null));
  }, []);

  const syncMatrixFromTask = useCallback(
    (data: TaskData) => {
      setTask(data);
      setMatrixRows((data.comparison_table?.matrix_rows as MatrixRow[]) || []);
      setConfirmed(data.status !== "draft");
      syncFromPayload(data);
    },
    [syncFromPayload],
  );

  const pollTask = useCallback(async (taskId: string) => {
    setAnalysisProgress(0);
    setAnalysisMessage("等待处理...");
    for (let i = 0; i < POLL_MAX_ITERATIONS; i++) {
      const statusResp = await apiClient.get<TaskStatusPayload>(`/rfq/tasks/${taskId}/status`);
      const status = statusResp.data;
      setAnalysisProgress(status.progress ?? 0);
      setAnalysisMessage(
        status.message || STAGE_LABELS[status.status] || "正在分析...",
      );
      if (status.status === "completed" || status.status === "failed") {
        const taskResp = await apiClient.get<{ code: number; data: TaskData }>(`/rfq/tasks/${taskId}`);
        syncMatrixFromTask(taskResp.data.data);
        if (status.status === "failed") {
          message.error("RFQ 分析失败");
        }
        setAnalysisProgress(status.status === "completed" ? 100 : 0);
        return;
      }
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    }
    message.warning("分析超时，请稍后刷新任务或检查 Ollama 是否响应");
  }, [syncMatrixFromTask]);

  const loadExistingTask = useCallback(async (taskId: string) => {
    const id = taskId.trim();
    if (!id) {
      setRestoring(false);
      return;
    }
    try {
      const statusResp = await apiClient.get<TaskStatusPayload>(`/rfq/tasks/${id}/status`);
      const status = statusResp.data;
      if (status.status === "completed" || status.status === "failed") {
        const taskResp = await apiClient.get<{ code: number; data: TaskData }>(`/rfq/tasks/${id}`);
        syncMatrixFromTask(taskResp.data.data);
        setAnalysisProgress(status.status === "completed" ? 100 : 0);
        setAnalysisMessage(status.message || STAGE_LABELS[status.status] || "");
      } else {
        setUploading(true);
        await pollTask(id);
      }
    } catch {
      // invalid stored id
    } finally {
      setRestoring(false);
      setUploading(false);
    }
  }, [pollTask, syncMatrixFromTask]);

  useEffect(() => {
    const stored =
      typeof window !== "undefined" ? sessionStorage.getItem("aria_last_task_id")?.trim() : "";
    if (stored) {
      void loadExistingTask(stored);
    } else {
      setRestoring(false);
    }
  }, [loadExistingTask]);

  const handleSelectRecentTask = async (taskId: string) => {
    setRestoring(true);
    await loadExistingTask(taskId);
    await loadTaskFromContext(taskId);
    await refreshRecentTasks();
  };

  const formatRecentLabel = (t: TaskSummary) => {
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
  };

  const handleUpload = async (file: File) => {
    setUploading(true);
    setTask(null);
    setMatrixRows([]);
    setConfirmed(false);
    setAnalysisProgress(0);
    setAnalysisMessage("");
    try {
      const form = new FormData();
      form.append("file", file);
      const resp = await apiClient.post<{ code: number; data: { task_id: string } }>(
        "/rfq/upload",
        form,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      message.success("上传成功，正在分析...");
      await refreshRecentTasks();
      await pollTask(resp.data.data.task_id);
    } finally {
      setUploading(false);
    }
    return false;
  };

  const handleNewProjectChange = (dimension: string, value: string) => {
    setMatrixRows((rows) =>
      rows.map((row) => (row.dimension === dimension ? { ...row, new_project: value } : row)),
    );
  };

  const handleSaveReview = async () => {
    if (!task) return;
    setSaving(true);
    try {
      const newRequirements = matrixRows.reduce<Record<string, string>>((acc, row) => {
        if (!row.dimension.startsWith("技术") && !row.dimension.includes("人天") && !row.dimension.includes("偏差")) {
          acc[row.dimension] = String(row.new_project);
        }
        return acc;
      }, {});

      const resp = await apiClient.put<{ code: number; data: TaskData }>(`/rfq/tasks/${task.task_id}`, {
        comparison_table: {
          ...task.comparison_table,
          matrix_rows: matrixRows,
          new_project_requirements: newRequirements,
        },
        confirmed,
      });
      syncMatrixFromTask(resp.data.data);
      message.success("已保存人工修订");
    } finally {
      setSaving(false);
    }
  };

  const modules = (task?.rfq_modules?.modules as Array<Record<string, unknown>>) || [];
  const milestones = (task?.rfq_modules?.milestones as Record<string, string>) || {};
  const specialReqs = (task?.rfq_modules?.special_requirements as string[]) || [];
  const projects = (task?.comparison_table?.projects as Array<Record<string, unknown>>) || [];
  const projectNames = projects.map((p) => String(p.project_name || "历史项目"));
  const allDeliverables = modules.flatMap((m) => (m.deliverables as string[]) || []);
  const confidence = (task?.comparison_table as { overall_confidence?: string })?.overall_confidence;
  const isLowConfidence = confidence === "低";

  return (
    <div>
      <Title level={3}>RFQ 分析</Title>
      <Paragraph type="secondary">
        上传客户 RFQ 文档（.docx），系统将解析 Function 模块、里程碑与交付物，并生成技术维度对比矩阵。
      </Paragraph>

      {recentTasks.length > 0 && (
        <Card title="最近分析" style={{ marginBottom: 24 }} size="small">
          <List
            size="small"
            dataSource={recentTasks.slice(0, 8)}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button
                    key="load"
                    type="link"
                    size="small"
                    onClick={() => void handleSelectRecentTask(item.task_id)}
                  >
                    加载
                  </Button>,
                ]}
              >
                {formatRecentLabel(item)}
              </List.Item>
            )}
          />
        </Card>
      )}

      <Card title="上传 RFQ" style={{ marginBottom: 24 }}>
        {uploading && (
          <div style={{ marginBottom: 16 }}>
            <Progress
              percent={analysisProgress}
              status={analysisProgress === 100 ? "success" : "active"}
              strokeColor={analysisProgress < 100 ? "#E30613" : undefined}
            />
            <Text type="secondary" style={{ display: "block", marginTop: 8 }}>
              {analysisMessage || "正在分析 RFQ..."}
            </Text>
            {useRealLlm && analysisProgress > 0 && analysisProgress < 50 && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                真实 LLM 模式下解析阶段可能需 1–2 分钟，请耐心等待
              </Text>
            )}
          </div>
        )}
        <Spin spinning={uploading} tip={analysisMessage || "正在分析 RFQ..."}>
          <Dragger
            multiple={false}
            accept=".docx"
            showUploadList={false}
            disabled={uploading}
            beforeUpload={(file) => {
              handleUpload(file as File);
              return false;
            }}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽 .docx 文件到此区域</p>
            <p className="ant-upload-hint">
              {useRealLlm === false
                ? "Mock 模式：规则提取；支持人工修订对比表"
                : useRealLlm
                  ? "真实 LLM 模式：Ollama 解析，请留意上方进度"
                  : "上传后自动触发异步分析"}
            </p>
          </Dragger>
        </Spin>
      </Card>

      {isLowConfidence && (
        <Alert
          type="error"
          showIcon
          message="匹配置信度较低"
          description="历史项目相似度不足，请人工核对对比矩阵后再确认进入报价流程。"
          style={{ marginBottom: 24, borderColor: "#E30613" }}
        />
      )}

      {task?.rfq_modules && (
        <>
          <Card title="RFQ 解析结果" style={{ marginBottom: 24 }}>
            <Descriptions column={2} size="small">
              <Descriptions.Item label="Task ID" span={2}>
                <Text copyable={{ text: task.task_id }}>{task.task_id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="项目">
                {String(task.rfq_modules.project_name || "-")}
              </Descriptions.Item>
              <Descriptions.Item label="客户">
                {String(task.rfq_modules.customer || "-")}
              </Descriptions.Item>
              <Descriptions.Item label="平台">
                {String(task.rfq_modules.platform_type || "-")}
              </Descriptions.Item>
              <Descriptions.Item label="周期">
                {String(task.rfq_modules.timeline_months || "-")} 月
              </Descriptions.Item>
            </Descriptions>

            {Object.keys(milestones).length > 0 && (
              <Descriptions column={3} size="small" title="里程碑" style={{ marginTop: 16 }}>
                {Object.entries(milestones).map(([k, v]) => (
                  <Descriptions.Item key={k} label={k}>
                    {v}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            )}

            <Table
              style={{ marginTop: 16 }}
              rowKey={(_, i) => String(i)}
              size="small"
              pagination={false}
              dataSource={modules}
              columns={[
                { title: "Function", dataIndex: "function" },
                { title: "模块", dataIndex: "module_name" },
                { title: "复杂度", dataIndex: "estimated_complexity" },
                {
                  title: "交付物",
                  dataIndex: "deliverables",
                  render: (items: string[]) => (items || []).join("；") || "—",
                },
              ]}
            />

            {allDeliverables.length > 0 && (
              <Collapse
                style={{ marginTop: 16 }}
                items={[
                  {
                    key: "deliverables",
                    label: `全部交付物（${allDeliverables.length} 项）`,
                    children: (
                      <List
                        size="small"
                        dataSource={allDeliverables}
                        renderItem={(item) => <List.Item>{item}</List.Item>}
                      />
                    ),
                  },
                ]}
              />
            )}

            {specialReqs.length > 0 && (
              <Alert
                style={{ marginTop: 16 }}
                type="info"
                message="特殊要求 / 假设"
                description={
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {specialReqs.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                }
              />
            )}
          </Card>

          <Card
            title={
              <Space>
                <span>技术维度对比矩阵</span>
                <Text type="secondary">置信度</Text>
                <ConfidenceBadge level={confidence} />
              </Space>
            }
            extra={
              (task.comparison_table as { recommendation?: string })?.recommendation && (
                <Text type="secondary">
                  {(task.comparison_table as { recommendation?: string }).recommendation}
                </Text>
              )
            }
            style={{ marginBottom: 24 }}
          >
            {matrixRows.length > 0 ? (
              <ComparisonMatrix
                matrixRows={matrixRows}
                projectNames={projectNames}
                editable
                onNewProjectChange={handleNewProjectChange}
              />
            ) : (
              <Alert message="暂无对比矩阵数据" type="warning" />
            )}

            <Space style={{ marginTop: 16 }}>
              <Checkbox checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)}>
                我已核对对比表，确认可进入报价参考
              </Checkbox>
              <Button type="primary" loading={saving} onClick={handleSaveReview}>
                保存修订
              </Button>
              {(task.status === "in_review" || confirmed) && (
                <Link href={`/proposal?task_id=${task.task_id}`}>
                  <Button type="primary">下一步：方案草案</Button>
                </Link>
              )}
            </Space>
          </Card>

          <Card title="相似项目检索摘要">
            <Table
              rowKey="project_name"
              size="small"
              dataSource={projects}
              pagination={false}
              expandable={{
                expandedRowRender: (row: Record<string, unknown>) => {
                  const dimensions = (row.dimensions as Record<string, Record<string, unknown>>) || {};
                  const rowName = String(row.project_name || "");
                  const similarHit = (task.similar_projects || []).find((s) => {
                    const meta = s.metadata as Record<string, unknown> | undefined;
                    return String(meta?.project_name || s.project_name || "") === rowName;
                  });
                  const chunkText = similarHit?.content ? String(similarHit.content).slice(0, 300) : "";
                  return (
                    <div style={{ padding: "8px 0" }}>
                      <Paragraph>
                        <Text strong>摘要：</Text>
                        {String(row.summary || "—")}
                      </Paragraph>
                      {chunkText ? (
                        <Paragraph>
                          <Text strong>检索片段：</Text>
                          {chunkText}
                        </Paragraph>
                      ) : null}
                      {Object.keys(dimensions).length > 0 && (
                        <Descriptions size="small" column={2} title="维度匹配">
                          {Object.entries(dimensions).map(([dim, info]) => (
                            <Descriptions.Item key={dim} label={dim}>
                              {String(info?.value ?? "—")}
                              {info?.match === true && " ✓"}
                              {info?.match === false && " ✗"}
                            </Descriptions.Item>
                          ))}
                        </Descriptions>
                      )}
                      <Paragraph type="secondary">
                        来源文档：{String(row.source_doc || "—")} · 实际人天{" "}
                        {String(row.actual_man_days ?? "—")} · 偏差 {String(row.deviation_rate ?? "—")}
                      </Paragraph>
                    </div>
                  );
                },
              }}
              columns={[
                { title: "项目", dataIndex: "project_name" },
                {
                  title: "相似度",
                  dataIndex: "similarity_score",
                  render: (v: number) => `${Math.round(v * 100)}%`,
                },
                { title: "来源", dataIndex: "source_doc" },
                { title: "摘要", dataIndex: "summary" },
              ]}
            />
          </Card>
        </>
      )}

      {!task && !uploading && !restoring && (
        <Alert
          message="提示"
          description="可使用 samples/rfq/mock_chassis_rfq.docx 进行 Demo 测试。"
          type="info"
          showIcon
        />
      )}

      {restoring && !task && (
        <div style={{ textAlign: "center", padding: 24 }}>
          <Spin tip="正在恢复上次分析结果..." />
        </div>
      )}
    </div>
  );
}
