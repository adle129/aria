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
  /** Increment to trigger the same action as「更新检索」. */
  startSignal?: number;
  /** Hide the start button when parent toolbar owns the CTA. */
  hideStartButton?: boolean;
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
  startSignal = 0,
  hideStartButton = false,
}: KnowledgeIndexJobPanelProps) {
  const [job, setJob] = useState<KnowledgeIndexJob | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [capacityError, setCapacityError] =
    useState<CapacityErrorData | null>(null);
  const completedJobs = useRef(new Set<string>());
  const failedJobs = useRef(new Set<string>());
  const [pollError, setPollError] = useState(false);

  const acceptJob = useCallback(
    async (next: KnowledgeIndexJob | null) => {
      setJob(next);
      if (!next) return;
      if (
        next.status === "completed" &&
        !completedJobs.current.has(next.job_id)
      ) {
        completedJobs.current.add(next.job_id);
        message.success(
          `更新完成：${next.new_documents ?? 0} 篇文档，${next.new_chunks ?? 0} 条知识`,
        );
        await onCompleted();
      }
      if (
        next.status === "failed" &&
        !failedJobs.current.has(next.job_id)
      ) {
        failedJobs.current.add(next.job_id);
        message.error(next.error || "检索更新失败，请查看下方项目列表状态");
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
      setPollError(false);
      await acceptJob(resp.data.data);
    },
    [acceptJob],
  );

  useEffect(() => {
    const loadInitialJob = async () => {
      try {
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
      } catch {
        setPollError(true);
      }
    };

    void loadInitialJob();
  }, [acceptJob]);

  useEffect(() => {
    if (!job || !ACTIVE_INDEX_JOB_STATUSES.has(job.status)) return;
    const timer = window.setInterval(() => {
      void loadJob(job.job_id).catch(() => setPollError(true));
    }, 2000);
    return () => window.clearInterval(timer);
  }, [job, loadJob]);

  const start = useCallback(async () => {
    if (writeProtected) {
      message.error("数据盘处于写保护，暂时无法更新检索");
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
          `更新完成：${resp.data.data.new_documents ?? 0} 篇文档，${resp.data.data.new_chunks ?? 0} 条知识`,
        );
        await onCompleted();
        return;
      }
      if (resp.data.data.reused) {
        message.info("已有更新任务，已显示当前进度");
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
  }, [loadJob, onCompleted, writeProtected]);

  useEffect(() => {
    if (startSignal > 0) {
      void start();
    }
  }, [startSignal, start]);

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

  const showBody =
    Boolean(job) ||
    Boolean(capacityError) ||
    pollError ||
    active ||
    submitting ||
    !hideStartButton;

  if (!showBody && hideStartButton) {
    return null;
  }

  return (
    <Card
      title="检索更新"
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
          {!hideStartButton && (
            <Button
              type="primary"
              size="small"
              loading={submitting}
              disabled={active || writeProtected}
              onClick={() => void start()}
            >
              更新检索
            </Button>
          )}
        </Space>
      }
    >
      {capacityError && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 12 }}
          role="alert"
          aria-live="assertive"
          message="更新检索所需空间不足"
          description={`需要保留 ${formatCapacityBytes(capacityError.required_bytes)}，当前可用 ${formatCapacityBytes(capacityError.available_bytes)}。请清理数据盘或联系 IT 扩容后再试。${capacityError.action ? `（${capacityError.action}）` : ""}`}
        />
      )}
      {pollError && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message="无法刷新更新任务状态"
          description="请检查网络或重新打开本页；任务可能仍在后台运行。"
        />
      )}
      {!job ? (
        <Text type="secondary">
          {pollError
            ? "暂时无法加载更新任务状态。"
            : hideStartButton
              ? "资料落盘或替换后不会自动进检索库；点击上方「更新检索」写入（仅重算有变更的项目）。"
              : "当前没有更新任务。添加历史项目后可启动更新。"}
        </Text>
      ) : (
        <Space direction="vertical" style={{ width: "100%" }} size={8}>
          <Space wrap>
            <Tag color={completedWithWarnings ? "warning" : STATUS_COLOR[job.status]}>
              {completedWithWarnings
                ? "完成（有警告）"
                : INDEX_JOB_STATUS_LABEL[job.status]}
            </Tag>
            <Text type="secondary">{phaseLabel}</Text>
            {job.queue_position != null && (
              <Text type="secondary">
                队列第 {job.queue_position} 位
                {job.estimated_wait_seconds != null && job.estimated_wait_seconds > 0
                  ? ` · 预计约 ${Math.ceil(job.estimated_wait_seconds / 60)} 分钟`
                  : ""}
              </Text>
            )}
          </Space>
          <Progress
            percent={
              job.status === "completed"
                ? 100
                : active
                  ? Math.min(job.progress ?? 0, 99)
                  : (job.progress ?? 0)
            }
            status={
              job.status === "failed"
                ? "exception"
                : active
                  ? "active"
                  : job.status === "completed"
                    ? "success"
                    : undefined
            }
          />
          {job.status === "completed" && (
            <Text type="secondary">
              新增 {job.new_documents ?? 0} 篇文档 · {job.new_chunks ?? 0} 条知识
              {(job.skipped ?? 0) > 0 ? ` · 跳过 ${job.skipped}` : ""}
            </Text>
          )}
          {job.error && <Alert type="error" showIcon message={job.error} />}
          {failedGuidance.length > 0 && (
            <Alert
              type="warning"
              showIcon
              message={`${failedGuidance.length} 个项目未能加入检索`}
              description={
                <div>
                  <ul style={{ margin: "6px 0 8px", paddingLeft: 18 }}>
                    {failedGuidance.slice(0, 8).map((failure, index) => (
                      <li key={`${failure.itemName}-${index}`}>
                        <Text strong>{failure.itemName}</Text>
                        <Text type="secondary">
                          {" — "}
                          {/信息不完整|项目信息|metadata/i.test(failure.reason)
                            ? "项目信息不完整（显示名、客户、年份、工程领域）"
                            : failure.reason.length > 80
                              ? `${failure.reason.slice(0, 80)}…`
                              : failure.reason}
                        </Text>
                      </li>
                    ))}
                    {failedGuidance.length > 8 ? (
                      <li>
                        <Text type="secondary">另有 {failedGuidance.length - 8} 项…</Text>
                      </li>
                    ) : null}
                  </ul>
                  <Text>
                    请在下方列表点击「完善信息」，保存后再点「更新检索」。
                  </Text>
                </div>
              }
            />
          )}
          <Collapse
            size="small"
            ghost
            items={[
              {
                key: "ops",
                label: <Text type="secondary">运维编号（排查用）</Text>,
                children: (
                  <Space direction="vertical" size={4}>
                    <Text type="secondary" copyable={{ text: job.job_id }}>
                      任务 {job.job_id}
                    </Text>
                    {job.import_id ? (
                      <Text type="secondary" copyable={{ text: job.import_id }}>
                        批次 {job.import_id}
                      </Text>
                    ) : null}
                    {(job.active_generation ?? job.generation_id) ? (
                      <Text
                        type="secondary"
                        copyable={{
                          text: String(job.active_generation ?? job.generation_id),
                        }}
                      >
                        Generation {job.active_generation ?? job.generation_id}
                      </Text>
                    ) : null}
                    {job.mode ? (
                      <Text type="secondary">
                        模式 {job.mode === "full" ? "全量" : "增量"}
                      </Text>
                    ) : null}
                  </Space>
                ),
              },
            ]}
          />
        </Space>
      )}
    </Card>
  );
}
