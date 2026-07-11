"use client";

import {
  Alert,
  Button,
  Card,
  Collapse,
  Progress,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import axios from "axios";
import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "@/api/client";
import {
  ACTIVE_INDEX_JOB_STATUSES,
  getKnowledgeIndexFailureGuidance,
  INDEX_JOB_PHASE_LABEL,
  INDEX_JOB_STATUS_LABEL,
  type KnowledgeIndexFailure,
  type KnowledgeIndexJobStatus,
} from "@/lib/knowledgeIndexJob";
import { formatCapacityBytes } from "@/lib/kbCapacity";

const { Text } = Typography;

interface KnowledgeIndexJob {
  job_id: string;
  status: KnowledgeIndexJobStatus;
  phase?: string | null;
  progress: number;
  progress_current: number;
  progress_total: number;
  queue_position?: number | null;
  estimated_wait_seconds?: number | null;
  generation_id?: string | null;
  active_generation?: string | null;
  previous_generation?: string | null;
  error?: string | null;
  new_documents?: number;
  new_chunks?: number;
  skipped?: number;
  failed_files?: KnowledgeIndexFailure[];
  triggered_by?: string | null;
  mode?: string | null;
  import_id?: string | null;
}

interface KnowledgeIndexJobPanelProps {
  onCompleted: () => void | Promise<void>;
  writeProtected?: boolean;
}

interface CapacityErrorData {
  required_bytes: number;
  available_bytes: number;
  action: string;
}

const STATUS_COLOR: Record<KnowledgeIndexJobStatus, string> = {
  queued: "default",
  running: "processing",
  cancelling: "warning",
  completed: "success",
  failed: "error",
  cancelled: "default",
};

export default function KnowledgeIndexJobPanel({
  onCompleted,
  writeProtected = false,
}: KnowledgeIndexJobPanelProps) {
  const [job, setJob] = useState<KnowledgeIndexJob | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [capacityError, setCapacityError] =
    useState<CapacityErrorData | null>(null);
  const completedJobs = useRef(new Set<string>());

  const acceptJob = useCallback(
    async (next: KnowledgeIndexJob | null) => {
      setJob(next);
      if (
        next?.status === "completed" &&
        !completedJobs.current.has(next.job_id)
      ) {
        completedJobs.current.add(next.job_id);
        message.success(
          `索引完成：${next.new_documents ?? 0} 篇文档，${next.new_chunks ?? 0} 个片段`,
        );
        await onCompleted();
      }
    },
    [onCompleted],
  );

  const loadJob = useCallback(
    async (jobId: string) => {
      const resp = await apiClient.get<{ code: number; data: KnowledgeIndexJob }>(
        `/knowledge/imports/${jobId}`,
        { silentError: true },
      );
      await acceptJob(resp.data.data);
    },
    [acceptJob],
  );

  useEffect(() => {
    const loadInitialJob = async () => {
      const activeResp = await apiClient.get<{
        code: number;
        data: KnowledgeIndexJob | null;
      }>("/knowledge/imports/active", { silentError: true });
      if (activeResp.data.data) {
        await acceptJob(activeResp.data.data);
        return;
      }

      const historyResp = await apiClient.get<{
        code: number;
        data: { jobs: KnowledgeIndexJob[] };
      }>("/knowledge/imports?limit=1&offset=0", { silentError: true });
      await acceptJob(historyResp.data.data.jobs[0] ?? null);
    };

    void loadInitialJob().catch(() => undefined);
  }, [acceptJob]);

  useEffect(() => {
    if (!job || !ACTIVE_INDEX_JOB_STATUSES.has(job.status)) return;
    const timer = window.setInterval(() => {
      void loadJob(job.job_id).catch(() => undefined);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [job, loadJob]);

  const start = async () => {
    if (writeProtected) {
      message.error("数据盘处于写保护，暂时无法更新索引");
      return;
    }
    setSubmitting(true);
    setCapacityError(null);
    try {
      const resp = await apiClient.post<{
        code: number;
        data: {
          job_id?: string;
          status?: KnowledgeIndexJobStatus;
          reused?: boolean;
          new_documents?: number;
          new_chunks?: number;
        };
      }>("/knowledge/import");
      if (!resp.data.data.job_id) {
        message.success(
          `索引完成：${resp.data.data.new_documents ?? 0} 篇文档，${resp.data.data.new_chunks ?? 0} 个片段`,
        );
        await onCompleted();
        return;
      }
      if (resp.data.data.reused) {
        message.info("已有索引任务，已显示当前进度");
      }
      await loadJob(resp.data.data.job_id);
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 507) {
        setCapacityError(error.response.data?.data ?? null);
      }
      return;
    } finally {
      setSubmitting(false);
    }
  };

  const cancel = async () => {
    if (!job) return;
    try {
      const resp = await apiClient.post<{ code: number; data: KnowledgeIndexJob }>(
        `/knowledge/imports/${job.job_id}/cancel`,
      );
      await acceptJob(resp.data.data);
    } catch {
      return;
    }
  };

  const active = job ? ACTIVE_INDEX_JOB_STATUSES.has(job.status) : false;
  const phaseLabel = job?.phase
    ? INDEX_JOB_PHASE_LABEL[job.phase] ?? job.phase
    : "等待任务";
  const failedGuidance =
    job?.failed_files?.map(getKnowledgeIndexFailureGuidance) ?? [];
  const completedWithWarnings =
    job?.status === "completed" && failedGuidance.length > 0;

  return (
    <Card
      title="知识库索引任务"
      size="small"
      style={{ marginBottom: 16 }}
      extra={
        <Space>
          {active && (
            <Button
              danger
              size="small"
              disabled={job?.status === "cancelling"}
              onClick={() => void cancel()}
            >
              取消
            </Button>
          )}
          <Button
            type="primary"
            size="small"
            loading={submitting}
            disabled={active || writeProtected}
            onClick={() => void start()}
          >
            更新知识库索引
          </Button>
        </Space>
      }
    >
      {capacityError && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 12 }}
          message="更新索引所需空间不足"
          description={`需要保留 ${formatCapacityBytes(capacityError.required_bytes)}，当前可用 ${formatCapacityBytes(capacityError.available_bytes)}。${capacityError.action}`}
        />
      )}
      {!job ? (
        <Text type="secondary">当前没有索引任务。上传项目包后可启动更新。</Text>
      ) : (
        <Space direction="vertical" style={{ width: "100%" }} size={8}>
          <Space wrap>
            <Tag color={completedWithWarnings ? "warning" : STATUS_COLOR[job.status]}>
              {completedWithWarnings
                ? "完成（有警告）"
                : INDEX_JOB_STATUS_LABEL[job.status]}
            </Tag>
            <Text>{phaseLabel}</Text>
            {job.mode && (
              <Text type="secondary">
                {job.mode === "full" ? "全量" : "增量"}
              </Text>
            )}
            {job.import_id && (
              <Text type="secondary" copyable={{ text: job.import_id }}>
                批次 {job.import_id.slice(0, 8)}
              </Text>
            )}
            {job.queue_position != null && <Text type="secondary">队列第 {job.queue_position} 位</Text>}
            {(job.active_generation ?? job.generation_id) && (
              <Text type="secondary" copyable>
                Generation {(job.active_generation ?? job.generation_id)?.slice(0, 8)}
              </Text>
            )}
          </Space>
          <Progress
            percent={job.status === "completed" ? 100 : job.progress}
            status={job.status === "failed" ? "exception" : undefined}
          />
          {job.status === "completed" && (
            <Text type="secondary">
              新增 {job.new_documents ?? 0} 篇文档，{job.new_chunks ?? 0} 个片段，跳过{" "}
              {job.skipped ?? 0} 篇
            </Text>
          )}
          {job.error && <Alert type="error" showIcon message={job.error} />}
          {failedGuidance.length > 0 && (
            <>
              <Alert
                type="warning"
                showIcon
                message={`${failedGuidance.length} 个项目未进入本次生效索引`}
                description="其余处理成功的项目已正常生效。请展开详情，修复资料后重新上传并再次更新索引。"
              />
              <Collapse
                size="small"
                items={[
                  {
                    key: "failed-files",
                    label: `查看 ${failedGuidance.length} 项失败详情与修复建议`,
                    children: (
                      <Space direction="vertical" size={12} style={{ width: "100%" }}>
                        {failedGuidance.map((failure, index) => (
                          <div
                            key={`${failure.itemName}-${index}`}
                            style={{
                              borderBottom:
                                index < failedGuidance.length - 1
                                  ? "1px solid #f0f0f0"
                                  : undefined,
                              paddingBottom:
                                index < failedGuidance.length - 1 ? 12 : 0,
                            }}
                          >
                            <Space direction="vertical" size={2}>
                              <Text strong>{failure.itemName}</Text>
                              <Text type="danger">失败原因：{failure.reason}</Text>
                              <Text>影响：{failure.impact}</Text>
                              <Text>处理建议：{failure.action}</Text>
                            </Space>
                          </div>
                        ))}
                      </Space>
                    ),
                  },
                ]}
              />
            </>
          )}
        </Space>
      )}
    </Card>
  );
}
