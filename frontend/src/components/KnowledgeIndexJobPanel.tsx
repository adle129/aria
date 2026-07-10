"use client";

import { Alert, Button, Card, Progress, Space, Tag, Typography, message } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "@/api/client";
import {
  ACTIVE_INDEX_JOB_STATUSES,
  INDEX_JOB_PHASE_LABEL,
  INDEX_JOB_STATUS_LABEL,
  type KnowledgeIndexJobStatus,
} from "@/lib/knowledgeIndexJob";

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
  failed_files?: Array<{ path: string; error: string }>;
}

interface KnowledgeIndexJobPanelProps {
  onCompleted: () => void | Promise<void>;
}

const STATUS_COLOR: Record<KnowledgeIndexJobStatus, string> = {
  queued: "default",
  running: "processing",
  cancelling: "warning",
  completed: "success",
  failed: "error",
  cancelled: "default",
};

export default function KnowledgeIndexJobPanel({ onCompleted }: KnowledgeIndexJobPanelProps) {
  const [job, setJob] = useState<KnowledgeIndexJob | null>(null);
  const [submitting, setSubmitting] = useState(false);
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
    void apiClient
      .get<{ code: number; data: KnowledgeIndexJob | null }>("/knowledge/imports/active", {
        silentError: true,
      })
      .then((resp) => acceptJob(resp.data.data))
      .catch(() => undefined);
  }, [acceptJob]);

  useEffect(() => {
    if (!job || !ACTIVE_INDEX_JOB_STATUSES.has(job.status)) return;
    const timer = window.setInterval(() => {
      void loadJob(job.job_id).catch(() => undefined);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [job, loadJob]);

  const start = async () => {
    setSubmitting(true);
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
    } catch {
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
            disabled={active}
            onClick={() => void start()}
          >
            更新知识库索引
          </Button>
        </Space>
      }
    >
      {!job ? (
        <Text type="secondary">当前没有索引任务。上传项目包后可启动更新。</Text>
      ) : (
        <Space direction="vertical" style={{ width: "100%" }} size={8}>
          <Space wrap>
            <Tag color={STATUS_COLOR[job.status]}>{INDEX_JOB_STATUS_LABEL[job.status]}</Tag>
            <Text>{phaseLabel}</Text>
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
          {(job.failed_files?.length ?? 0) > 0 && (
            <Alert
              type="warning"
              showIcon
              message={`${job.failed_files?.length} 个项目处理失败`}
            />
          )}
        </Space>
      )}
    </Card>
  );
}
