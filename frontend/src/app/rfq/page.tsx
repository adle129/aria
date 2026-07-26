"use client";

import {
  Alert,
  Button,
  Card,
  Checkbox,
  List,
  Modal,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient, clearStoredTaskId, fetchHealth, retryTask } from "@/api/client";
import DemoModuleCapability from "@/components/DemoModuleCapability";
import DimensionBaselineReview, { type DimensionDraft } from "@/components/DimensionBaselineReview";
import { ComparisonMatrix, ConfidenceBadge, type MatrixRow } from "@/components/ComparisonMatrix";
import RfqAnalysisProgress from "@/components/rfq/RfqAnalysisProgress";
import RfqParseSummary from "@/components/rfq/RfqParseSummary";
import RfqTaskHeader from "@/components/rfq/RfqTaskHeader";
import RfqUploadZone from "@/components/rfq/RfqUploadZone";
import WorkflowSteps from "@/components/WorkflowSteps";
import { useUiProfile } from "@/hooks/useUiProfile";
import { TASK_CHANGED_EVENT, notifyTaskChanged, useTaskContext } from "@/context/TaskContext";
import { isCancellingUi, shouldApplyStatusToDisplayedTask } from "@/lib/rfqCancelUi";
import { resolveStatusWatchTaskId, RfqPollSessionMap } from "@/lib/rfqStatusPoll";
import { RFQ_BEGIN_NEW_EVENT, RFQ_BEGIN_NEW_FLAG, resolveRfqWorkspaceStage } from "@/lib/rfqWorkspace";
import {
  buildBaselinesKnowledgeHref,
  resolveEngagementId,
  resolveProjectBaselinesEngagementIds,
} from "@/lib/rfqBaselinesLink";
import { PROCESSING_STATUS_LABELS } from "@/lib/taskStatus";
import type { ArtifactsStatus, TaskPayload } from "@/types/task";
const { Paragraph, Title, Text } = Typography;

interface TaskData extends TaskPayload {}

interface TaskStatusPayload {
  status: string;
  progress: number;
  message: string;
  queue_position?: number | null;
  estimated_wait_seconds?: number | null;
  queue_wait_ms?: number | null;
  run_ms?: number | null;
  queued_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

const POLL_INTERVAL_MS = 500;
/** Real LLM dimension match can exceed 3 min; align with backend ollama timeout window. */
const POLL_MAX_ITERATIONS = 1800;

function buildPendingTask(taskId: string, fileName: string): TaskData {
  return {
    task_id: taskId,
    file_name: fileName,
    processing_status: "queued",
    status: "draft",
    status_message: "排队等待处理",
  };
}

function deriveProcessingArtifacts(progress: number, processingStatus: string): ArtifactsStatus {
  const rfqParsed =
    !["queued", "pending"].includes(processingStatus) &&
    (processingStatus !== "parsing" || progress >= 20);
  return {
    rfq_parsed: rfqParsed,
    comparison_ready: processingStatus === "completed",
    proposal_ready: false,
    qa_ready: false,
    excel_ready: false,
  };
}

const IN_FLIGHT_PROCESSING = new Set([
  "queued",
  "pending",
  "parsing",
  "retrieving",
  "generating",
  "cancelling",
]);

function buildKnowledgeVerifyQuery(task: TaskData): string {
  const mods = task.rfq_modules as Record<string, unknown> | undefined;
  if (!mods) return "MEB 底盘";
  const parts: string[] = [];
  if (mods.platform_type) parts.push(String(mods.platform_type));
  if (Array.isArray(mods.functions_in_scope)) {
    parts.push(...mods.functions_in_scope.slice(0, 2).map(String));
  }
  return parts.join(" ").trim() || "MEB 底盘";
}

export default function RfqPage() {
  const { showDemoChrome, isFormalDelivery } = useUiProfile();
  const {
    syncFromPayload,
    refreshRecentTasks,
    clearTask,
    recentTasks,
  } = useTaskContext();
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [task, setTask] = useState<TaskData | null>(null);
  const [matrixRows, setMatrixRows] = useState<MatrixRow[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisMessage, setAnalysisMessage] = useState("");
  const [queuePosition, setQueuePosition] = useState<number | null>(null);
  const [estimatedWaitSeconds, setEstimatedWaitSeconds] = useState<number | null>(null);
  const [queueWaitMs, setQueueWaitMs] = useState<number | null>(null);
  const [runMs, setRunMs] = useState<number | null>(null);
  const [useRealLlm, setUseRealLlm] = useState<boolean | null>(null);
  const [restoring, setRestoring] = useState(true);
  const [demoSamples, setDemoSamples] = useState<
    Array<{ filename: string; title: string; description: string; download_url: string }>
  >([]);
  const [dimensionDraft, setDimensionDraft] = useState<DimensionDraft | null>(null);
  const [confirmingDimensions, setConfirmingDimensions] = useState(false);
  /** Only the task currently being cancelled — must not leak to other selected tasks. */
  const [cancellingTaskId, setCancellingTaskId] = useState<string | null>(null);
  const uploadInputRef = useRef<HTMLInputElement>(null);
  /** Per-task poll epochs — concurrent RFQ polls must not cancel each other. */
  const pollSessionsRef = useRef(new RfqPollSessionMap());
  const displayedTaskIdRef = useRef<string | null>(null);
  const [taskSwitching, setTaskSwitching] = useState(false);
  const [stalledPolling, setStalledPolling] = useState(false);
  /** Resume target for the displayed task's poll (not a sibling upload). */
  const [activePollTaskId, setActivePollTaskId] = useState<string | null>(null);

  useEffect(() => {
    displayedTaskIdRef.current = task?.task_id ?? null;
  }, [task?.task_id]);

  useEffect(() => {
    fetchHealth()
      .then((h) => setUseRealLlm(!h.mock_llm))
      .catch(() => setUseRealLlm(null));
  }, []);

  useEffect(() => {
    if (!showDemoChrome) return;
    apiClient
      .get<{
        code: number;
        data: {
          samples: Array<{
            filename: string;
            title: string;
            description: string;
            download_url: string;
          }>;
        };
      }>("/demo/rfq-samples", { silentError: true })
      .then((resp) => setDemoSamples(resp.data.data?.samples ?? []))
      .catch(() => setDemoSamples([]));
  }, [showDemoChrome]);

  const syncMatrixFromTask = useCallback(
    (data: TaskData) => {
      setTask(data);
      setMatrixRows((data.comparison_table?.matrix_rows as MatrixRow[]) || []);
      setConfirmed(data.status !== "draft");
      setDimensionDraft((data.dimension_draft as DimensionDraft) || null);
      syncFromPayload(data);
    },
    [syncFromPayload],
  );

  const resetWorkspace = useCallback(() => {
    pollSessionsRef.current.invalidateAll();
    if (typeof window !== "undefined") {
      sessionStorage.removeItem(RFQ_BEGIN_NEW_FLAG);
    }
    clearTask();
    setTask(null);
    setMatrixRows([]);
    setConfirmed(false);
    setDimensionDraft(null);
    setAnalysisProgress(0);
    setAnalysisMessage("");
    setQueuePosition(null);
    setEstimatedWaitSeconds(null);
    setQueueWaitMs(null);
    setRunMs(null);
    setUploading(false);
    setRestoring(false);
    setTaskSwitching(false);
    setStalledPolling(false);
    setActivePollTaskId(null);
    setCancellingTaskId(null);
  }, [clearTask]);

  const pollUntilTerminal = useCallback(
    async (
      taskId: string,
      stopAt: "dimension_review" | "completed",
      options?: { resume?: boolean },
    ) => {
      const sessions = pollSessionsRef.current;
      const myEpoch = sessions.begin(taskId);
      const isLive = () => sessions.isCurrent(taskId, myEpoch);
      const finishPoll = () => {
        sessions.end(taskId, myEpoch);
        setActivePollTaskId((prev) => (prev === taskId ? null : prev));
      };

      if (shouldApplyStatusToDisplayedTask(displayedTaskIdRef.current, taskId)) {
        setActivePollTaskId(taskId);
        setStalledPolling(false);
        if (!options?.resume) {
          setAnalysisProgress(0);
          setAnalysisMessage("等待处理...");
          setQueuePosition(null);
          setEstimatedWaitSeconds(null);
          setQueueWaitMs(null);
          setRunMs(null);
        }
      }

      let lastStatus = "";
      let lastProgress = -1;

      const applyStatus = (status: TaskStatusPayload) => {
        if (!shouldApplyStatusToDisplayedTask(displayedTaskIdRef.current, taskId)) return;
        setAnalysisProgress(status.progress ?? 0);
        setQueuePosition(status.queue_position ?? null);
        setEstimatedWaitSeconds(status.estimated_wait_seconds ?? null);
        setQueueWaitMs(status.queue_wait_ms ?? null);
        setRunMs(status.run_ms ?? null);
        setAnalysisMessage(status.message || PROCESSING_STATUS_LABELS[status.status] || "正在分析...");
        setTask((prev) =>
          prev && prev.task_id === taskId
            ? {
                ...prev,
                processing_status: status.status,
                status_message: status.message,
                queue_wait_ms: status.queue_wait_ms,
                run_ms: status.run_ms,
                queued_at: status.queued_at,
                started_at: status.started_at,
                finished_at: status.finished_at,
              }
            : prev,
        );
      };

      const applyTerminalTask = (data: TaskData, status: TaskStatusPayload) => {
        void refreshRecentTasks();
        if (!shouldApplyStatusToDisplayedTask(displayedTaskIdRef.current, taskId)) {
          return;
        }
        syncMatrixFromTask(data);
        if (status.status === "failed") {
          message.error(status.message || "RFQ 分析失败");
        }
        if (status.status === "cancelled") {
          setCancellingTaskId((id) => (id === taskId ? null : id));
        }
        setAnalysisProgress(status.status === "completed" ? 100 : status.progress ?? 0);
        setStalledPolling(false);
      };

      for (let i = 0; i < POLL_MAX_ITERATIONS; i++) {
        if (!isLive()) return "cancelled";
        let status: TaskStatusPayload;
        try {
          const statusResp = await apiClient.get<TaskStatusPayload>(
            `/rfq/tasks/${taskId}/status`,
            { silentError: true },
          );
          status = statusResp.data;
        } catch {
          if (!isLive()) return "cancelled";
          if (shouldApplyStatusToDisplayedTask(displayedTaskIdRef.current, taskId)) {
            setStalledPolling(true);
            setActivePollTaskId(taskId);
            setAnalysisMessage("状态查询暂时失败，后台可能仍在处理，请稍后继续等待");
          }
          await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS * 2));
          continue;
        }
        if (!isLive()) return "cancelled";
        const progress = status.progress ?? 0;
        if (status.status !== lastStatus) {
          lastStatus = status.status;
          void refreshRecentTasks();
        } else if (progress !== lastProgress) {
          lastProgress = progress;
          void refreshRecentTasks();
        }
        applyStatus(status);
        if (status.status === "cancelling") {
          setCancellingTaskId(taskId);
        }
        const done =
          status.status === "failed" ||
          status.status === "cancelled" ||
          status.status === stopAt ||
          (stopAt === "completed" && status.status === "completed");
        if (done) {
          const taskResp = await apiClient.get<{ code: number; data: TaskData }>(
            `/rfq/tasks/${taskId}`,
          );
          if (!isLive()) return "cancelled";
          applyTerminalTask(taskResp.data.data, status);
          finishPoll();
          return status.status;
        }
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
      }
      if (isLive()) {
        try {
          const statusResp = await apiClient.get<TaskStatusPayload>(`/rfq/tasks/${taskId}/status`);
          const status = statusResp.data;
          applyStatus(status);
          if (
            status.status === "failed" ||
            status.status === "cancelled" ||
            status.status === stopAt ||
            (stopAt === "completed" && status.status === "completed")
          ) {
            const taskResp = await apiClient.get<{ code: number; data: TaskData }>(
              `/rfq/tasks/${taskId}`,
            );
            if (!isLive()) return "cancelled";
            applyTerminalTask(taskResp.data.data, status);
            finishPoll();
            return status.status;
          }
        } catch {
          // fall through to stalled UI
        }
        if (shouldApplyStatusToDisplayedTask(displayedTaskIdRef.current, taskId)) {
          setStalledPolling(true);
          setActivePollTaskId(taskId);
          message.warning("分析耗时较长，后台可能仍在处理，可继续等待或稍后从左侧打开任务");
        }
        void refreshRecentTasks();
        // Keep session active so resume can continue this task.
        return "timeout";
      }
      return "cancelled";
    },
    [refreshRecentTasks, syncMatrixFromTask],
  );

  const pollTask = useCallback(
    async (taskId: string, resume = false) => pollUntilTerminal(taskId, "dimension_review", { resume }),
    [pollUntilTerminal],
  );

  const handleResumePolling = useCallback(async () => {
    const resumeId =
      (task?.task_id && activePollTaskId === task.task_id ? task.task_id : null) ??
      activePollTaskId ??
      task?.task_id;
    if (!resumeId) return;
    setUploading(true);
    setStalledPolling(false);
    const phase2Resume =
      task?.task_id === resumeId &&
      (task.processing_status === "retrieving" ||
        task.processing_status === "generating" ||
        (task.processing_status === "queued" &&
          Boolean(task.status_message?.includes("对比"))));
    await pollUntilTerminal(resumeId, phase2Resume ? "completed" : "dimension_review", {
      resume: true,
    });
    setUploading(false);
  }, [activePollTaskId, pollUntilTerminal, task]);

  const loadExistingTask = useCallback(async (taskId: string) => {
    const id = taskId.trim();
    if (!id) {
      setRestoring(false);
      return;
    }
    const silent = { silentError: true } as const;
    try {
      const statusResp = await apiClient.get<TaskStatusPayload>(
        `/rfq/tasks/${id}/status`,
        silent,
      );
      const status = statusResp.data;
      if (
        status.status === "completed" ||
        status.status === "failed" ||
        status.status === "dimension_review"
      ) {
        const taskResp = await apiClient.get<{ code: number; data: TaskData }>(
          `/rfq/tasks/${id}`,
          silent,
        );
        syncMatrixFromTask(taskResp.data.data);
        setAnalysisProgress(
          status.status === "completed" ? 100 : status.status === "dimension_review" ? 40 : 0,
        );
        setAnalysisMessage(status.message || PROCESSING_STATUS_LABELS[status.status] || "");
        setUploading(false);
        setStalledPolling(false);
        setActivePollTaskId(null);
      } else {
        let taskData: TaskData;
        try {
          const taskResp = await apiClient.get<{ code: number; data: TaskData }>(
            `/rfq/tasks/${id}`,
            silent,
          );
          taskData = taskResp.data.data;
        } catch {
          const hit = recentTasks.find((t) => t.task_id === id);
          taskData = {
            ...buildPendingTask(id, hit?.file_name ?? "RFQ"),
            processing_status: status.status,
            status_message: status.message,
          };
        }
        setTask(taskData);
        syncFromPayload(taskData);
        setAnalysisProgress(status.progress ?? 0);
        setAnalysisMessage(
          status.message || PROCESSING_STATUS_LABELS[status.status] || "正在分析...",
        );
        setQueuePosition(status.queue_position ?? null);
        setEstimatedWaitSeconds(status.estimated_wait_seconds ?? null);
        setQueueWaitMs(status.queue_wait_ms ?? null);
        setRunMs(status.run_ms ?? null);
        setActivePollTaskId(id);
        setStalledPolling(false);
        setUploading(true);
        void pollTask(id, true);
      }
    } catch (err) {
      if ((err as { response?: { status?: number } })?.response?.status === 404) {
        clearStoredTaskId();
        clearTask();
      }
    } finally {
      setRestoring(false);
    }
  }, [clearTask, pollTask, recentTasks, syncFromPayload, syncMatrixFromTask]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (sessionStorage.getItem(RFQ_BEGIN_NEW_FLAG) === "1") {
      resetWorkspace();
      return;
    }
    const stored = sessionStorage.getItem("aria_last_task_id")?.trim();
    if (stored) {
      void loadExistingTask(stored);
    } else {
      setRestoring(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount restore only
  }, []);

  useEffect(() => {
    const onBeginNew = () => resetWorkspace();
    window.addEventListener(RFQ_BEGIN_NEW_EVENT, onBeginNew);
    return () => window.removeEventListener(RFQ_BEGIN_NEW_EVENT, onBeginNew);
  }, [resetWorkspace]);

  useEffect(() => {
    const onTaskChanged = (e: Event) => {
      const newId = (e as CustomEvent<string>).detail?.trim();
      if (!newId) return;
      if (task?.task_id === newId && !taskSwitching) return;
      setTaskSwitching(true);
      void loadExistingTask(newId).finally(() => setTaskSwitching(false));
    };
    window.addEventListener(TASK_CHANGED_EVENT, onTaskChanged);
    return () => window.removeEventListener(TASK_CHANGED_EVENT, onTaskChanged);
  }, [loadExistingTask, task?.task_id, taskSwitching]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setTask(null);
    setMatrixRows([]);
    setConfirmed(false);
    setDimensionDraft(null);
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
      const newTaskId = resp.data.data.task_id;
      const pending = buildPendingTask(newTaskId, file.name);
      setTask(pending);
      syncFromPayload(pending);
      notifyTaskChanged(newTaskId);
      message.success("上传成功，正在分析...");
      await refreshRecentTasks();
      const result = await pollTask(newTaskId);
      if (result === "timeout") {
        setUploading(false);
        return false;
      }
    } finally {
      setUploading(false);
    }
    return false;
  };

  const handleRetry = useCallback(async () => {
    if (!task) return;
    const taskId = task.task_id;
    setUploading(true);
    setCancellingTaskId(null);
    setMatrixRows([]);
    setConfirmed(false);
    setDimensionDraft(null);
    setAnalysisProgress(0);
    setAnalysisMessage("");
    try {
      await retryTask(taskId);
      message.success("已重新排队，正在分析...");
      await refreshRecentTasks();
      const result = await pollTask(taskId);
      if (result === "timeout") {
        setUploading(false);
        return;
      }
    } catch {
      // error shown by interceptor
    } finally {
      setUploading(false);
    }
  }, [task, pollTask, refreshRecentTasks]);

  const handleCancelAnalysis = useCallback(async () => {
    if (!task) return;
    const taskId = task.task_id;
    setCancellingTaskId(taskId);
    try {
      const resp = await apiClient.post<{ code: number; data: TaskStatusPayload }>(
        `/rfq/tasks/${taskId}/cancel`,
      );
      const status = resp.data.data;
      if (shouldApplyStatusToDisplayedTask(displayedTaskIdRef.current, taskId)) {
        setAnalysisProgress(status.progress ?? 0);
        setAnalysisMessage(status.message || PROCESSING_STATUS_LABELS[status.status] || "");
        setQueueWaitMs(status.queue_wait_ms ?? null);
        setRunMs(status.run_ms ?? null);
        setTask((prev) =>
          prev && prev.task_id === taskId
            ? {
                ...prev,
                processing_status: status.status,
                status_message: status.message,
                queue_wait_ms: status.queue_wait_ms,
                run_ms: status.run_ms,
                queued_at: status.queued_at,
                started_at: status.started_at,
                finished_at: status.finished_at,
              }
            : prev,
        );
      }
      if (status.status === "cancelled") {
        if (shouldApplyStatusToDisplayedTask(displayedTaskIdRef.current, taskId)) {
          const taskResp = await apiClient.get<{ code: number; data: TaskData }>(
            `/rfq/tasks/${taskId}`,
          );
          syncMatrixFromTask(taskResp.data.data);
          setUploading(false);
          setActivePollTaskId(null);
          message.info("分析已取消");
        }
        setCancellingTaskId((id) => (id === taskId ? null : id));
        void refreshRecentTasks();
      }
    } catch {
      setCancellingTaskId((id) => (id === taskId ? null : id));
    }
  }, [task, refreshRecentTasks, syncMatrixFromTask]);

  const triggerUploadPicker = useCallback(() => {
    uploadInputRef.current?.click();
  }, []);

  const handleUploadNewRequest = useCallback(() => {
    if (!task || task.processing_status === "failed" || task.processing_status === "cancelled") {
      triggerUploadPicker();
      return;
    }
    const inFlight = IN_FLIGHT_PROCESSING.has(task.processing_status);
    if (inFlight) {
      Modal.confirm({
        title: "当前任务仍在分析中",
        content: "建议先取消当前分析再上传新 RFQ，以免占用模型资源。也可保留当前任务并继续上传。",
        okText: "先取消当前分析",
        cancelText: "继续上传新文件",
        onOk: () => void handleCancelAnalysis(),
        onCancel: () => {
          Modal.confirm({
            title: "上传新 RFQ",
            content: "上传新文件后，当前任务将保留在历史列表，可随时从左侧切回。确认继续？",
            okText: "继续上传",
            cancelText: "返回",
            onOk: triggerUploadPicker,
          });
        },
      });
      return;
    }
    Modal.confirm({
      title: "上传新 RFQ",
      content: "上传新文件后，当前任务将保留在历史列表，可随时从左侧切回。确认继续？",
      okText: "继续上传",
      cancelText: "取消",
      onOk: triggerUploadPicker,
    });
  }, [task, triggerUploadPicker, handleCancelAnalysis]);

  const handleTrySample = async (filename: string) => {
    try {
      const resp = await apiClient.get(`/demo/rfq-samples/${filename}`, {
        responseType: "blob",
      });
      const file = new File([resp.data], filename, {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      });
      await handleUpload(file);
    } catch {
      message.error("加载演示样例失败，请尝试下载后手动上传");
    }
  };

  const handleNewProjectChange = (dimension: string, value: string) => {
    setMatrixRows((rows) =>
      rows.map((row) => (row.dimension === dimension ? { ...row, new_project: value } : row)),
    );
  };

  const handleSaveDimensionDraft = async () => {
    if (!task || !dimensionDraft) return;
    setSaving(true);
    try {
      const resp = await apiClient.put<{ code: number; data: TaskData }>(`/rfq/tasks/${task.task_id}`, {
        dimension_draft: dimensionDraft,
      });
      syncMatrixFromTask(resp.data.data);
      message.success("已保存维度勾选");
    } finally {
      setSaving(false);
    }
  };

  const handleConfirmDimensions = async () => {
    if (!task || !dimensionDraft) return;
    setConfirmingDimensions(true);
    setUploading(true);
    try {
      const resp = await apiClient.post<{
        code: number;
        data: {
          processing_status: string;
          task?: TaskData;
        };
      }>(`/rfq/tasks/${task.task_id}/confirm-dimensions`, {
        baseline_version: dimensionDraft.baseline_version,
        items: dimensionDraft.items,
        custom_items: dimensionDraft.custom_items || [],
      });
      const resultStatus = resp.data.data.processing_status;
      if (resultStatus === "dimension_review") {
        if (resp.data.data.task) {
          syncMatrixFromTask(resp.data.data.task);
        }
        message.info("矩阵生成已取消，可重新确认维度");
        return;
      }
      message.success("已确认维度，正在生成对比矩阵...");
      const pollResult = await pollUntilTerminal(task.task_id, "completed");
      // Sibling uploads must not leave this task stuck mid-Phase2; re-fetch if poll ended early.
      if (pollResult !== "completed" && pollResult !== "failed" && pollResult !== "cancelled") {
        const taskResp = await apiClient.get<{ code: number; data: TaskData }>(
          `/rfq/tasks/${task.task_id}`,
          { silentError: true },
        );
        if (shouldApplyStatusToDisplayedTask(displayedTaskIdRef.current, task.task_id)) {
          syncMatrixFromTask(taskResp.data.data);
        }
        void refreshRecentTasks();
      }
    } catch {
      try {
        const taskResp = await apiClient.get<{ code: number; data: TaskData }>(
          `/rfq/tasks/${task.task_id}`,
          { silentError: true },
        );
        syncMatrixFromTask(taskResp.data.data);
      } catch {
        /* keep current UI; interceptor already toasted API error */
      }
    } finally {
      setConfirmingDimensions(false);
      setUploading(false);
    }
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

  const projects = (task?.comparison_table?.projects as Array<Record<string, unknown>>) || [];
  const projectNames = projects.map((p) => String(p.project_name || "历史项目"));
  const projectBaselinesEngagementIds = resolveProjectBaselinesEngagementIds(
    projects,
    task?.similar_projects,
  );
  const confidence = (task?.comparison_table as { overall_confidence?: string })?.overall_confidence;
  const isLowConfidence = confidence === "低";
  const insufficientEvidence = Boolean(
    (task?.comparison_table as { insufficient_evidence?: boolean })?.insufficient_evidence,
  );
  const functionCoverage = (
    task?.comparison_table as {
      function_coverage?: { uncovered?: string[]; in_scope?: string[] };
    }
  )?.function_coverage;
  const uncoveredFunctions = functionCoverage?.uncovered || [];
  const workspaceStage = resolveRfqWorkspaceStage(task, {
    uploading,
    restoring,
    hasMatrix: matrixRows.length > 0,
  });

  useEffect(() => {
    // Always follow the displayed task — never a sibling upload's activePollTaskId.
    const taskId = resolveStatusWatchTaskId({
      displayedTaskId: task?.task_id,
      activePollTaskId: null,
    });
    if (!taskId || !task) return;
    const shouldWatch =
      (stalledPolling && activePollTaskId === taskId) ||
      IN_FLIGHT_PROCESSING.has(task.processing_status);
    if (!shouldWatch) return;

    const syncStatus = async () => {
      try {
        const statusResp = await apiClient.get<TaskStatusPayload>(`/rfq/tasks/${taskId}/status`, {
          silentError: true,
        });
        const status = statusResp.data;
        if (!shouldApplyStatusToDisplayedTask(displayedTaskIdRef.current, taskId)) return;
        if (["dimension_review", "completed", "failed", "cancelled"].includes(status.status)) {
          const taskResp = await apiClient.get<{ code: number; data: TaskData }>(
            `/rfq/tasks/${taskId}`,
            { silentError: true },
          );
          syncMatrixFromTask(taskResp.data.data);
          setStalledPolling(false);
          setUploading(false);
          setActivePollTaskId((prev) => (prev === taskId ? null : prev));
          pollSessionsRef.current.invalidate(taskId);
          void refreshRecentTasks();
          return;
        }
        setAnalysisProgress(status.progress ?? 0);
        setAnalysisMessage(
          status.message || PROCESSING_STATUS_LABELS[status.status] || "正在分析...",
        );
        setTask((prev) =>
          prev && prev.task_id === taskId
            ? {
                ...prev,
                processing_status: status.status,
                status_message: status.message,
              }
            : prev,
        );
      } catch {
        // background sync is best-effort
      }
    };

    void syncStatus();
    const interval = setInterval(() => void syncStatus(), 3000);
    return () => clearInterval(interval);
  }, [
    activePollTaskId,
    task,
    task?.task_id,
    task?.processing_status,
    stalledPolling,
    syncMatrixFromTask,
    refreshRecentTasks,
  ]);

  const showEmptyUpload = workspaceStage === "empty" && !stalledPolling;
  const showProcessing = workspaceStage === "processing" || stalledPolling;
  const inDimensionReview = workspaceStage === "dimension_review";
  const showComparisonMatrix = workspaceStage === "matrix";
  const showFailed = workspaceStage === "failed";
  const showCancelled = workspaceStage === "cancelled";

  const renderMainWorkspace = () => {
    if (taskSwitching) {
      return (
        <div style={{ textAlign: "center", padding: 48 }}>
          <Spin tip="正在加载任务..." />
        </div>
      );
    }

    if (restoring && !task) {
      return (
        <div style={{ textAlign: "center", padding: 48 }}>
          <Spin tip="正在恢复上次分析结果..." />
        </div>
      );
    }

    if (showProcessing) {
      return (
        <RfqAnalysisProgress
          progress={analysisProgress}
          message={analysisMessage}
          processingStatus={task?.processing_status ?? "pending"}
          queuePosition={queuePosition}
          estimatedWaitSeconds={estimatedWaitSeconds}
          queueWaitMs={queueWaitMs}
          runMs={runMs}
          useRealLlm={useRealLlm}
          stalled={stalledPolling}
          cancelling={isCancellingUi({
            cancellingTaskId,
            displayedTaskId: task?.task_id,
            processingStatus: task?.processing_status,
          })}
          onResumePolling={() => void handleResumePolling()}
          onCancel={() => void handleCancelAnalysis()}
        />
      );
    }

    if (showCancelled && task) {
      return (
        <div style={{ maxWidth: 480, margin: "40px auto", textAlign: "center" }}>
          <Title level={4} style={{ fontWeight: 500, marginBottom: 8 }}>
            分析已取消
          </Title>
          <Paragraph type="secondary" style={{ marginBottom: 24 }}>
            {task.status_message || "本次分析已停止，已消耗的计算不会保留。"}
          </Paragraph>
          <Space>
            <Button type="primary" loading={uploading} onClick={() => void handleRetry()}>
              重新解析
            </Button>
            <Button onClick={triggerUploadPicker}>重新上传</Button>
          </Space>
        </div>
      );
    }

    if (showFailed && task) {
      const failHint = (() => {
        const err = (task.error_msg || "").toLowerCase();
        const msg = task.status_message || "";
        if (
          err.includes("ollama") ||
          err.includes("lease") ||
          err.includes("embedding") ||
          msg.includes("模型") ||
          msg.includes("检索")
        ) {
          return "相似项目检索或本地模型暂时不可用。请确认 Ollama 正常、知识库未在全量索引，然后重试。";
        }
        if (err.includes("timeout") || msg.includes("超时")) {
          return "处理超时。请稍后重试；若反复出现，请联系管理员检查 worker 与模型负载。";
        }
        return "可能是文档格式不标准或内容过短。您可以重新解析（使用同一文件）或重新上传。";
      })();
      return (
        <div style={{ maxWidth: 480, margin: "40px auto", textAlign: "center" }}>
          <Title level={4} style={{ fontWeight: 500, marginBottom: 8 }}>
            这份 RFQ 没能完成分析
          </Title>
          <Paragraph type="secondary" style={{ marginBottom: 12 }}>
            {failHint}
          </Paragraph>
          <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
            任务 ID：{task.task_id}
          </Paragraph>
          {task.error_msg || task.status_message ? (
            <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 24 }}>
              {task.status_message || task.error_msg}
              {task.error_msg && task.status_message !== task.error_msg
                ? `（${task.error_msg}）`
                : ""}
            </Paragraph>
          ) : null}
          <Space>
            <Button type="primary" loading={uploading} onClick={() => void handleRetry()}>
              重新解析
            </Button>
            <Button onClick={triggerUploadPicker}>重新上传</Button>
          </Space>
        </div>
      );
    }

    if (showEmptyUpload) {
      return (
        <RfqUploadZone
          disabled={uploading}
          useRealLlm={useRealLlm}
          showDemoChrome={showDemoChrome}
          onUpload={(file) => void handleUpload(file)}
        />
      );
    }

    if (!task) return null;

    return (
      <>
        <RfqTaskHeader task={task} onUploadNew={handleUploadNewRequest} />

        {task.rfq_modules && (
          <RfqParseSummary task={task} defaultExpanded={false} />
        )}

        {inDimensionReview && dimensionDraft && (
          <Card title="基准维度确认" style={{ marginBottom: 16 }}>
            <DimensionBaselineReview
              draft={dimensionDraft}
              saving={saving}
              confirming={confirmingDimensions}
              onDraftChange={setDimensionDraft}
              onSaveDraft={() => void handleSaveDimensionDraft()}
              onConfirm={() => void handleConfirmDimensions()}
            />
          </Card>
        )}

        {showComparisonMatrix && (
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
            style={{ marginBottom: 16 }}
          >
            {insufficientEvidence && (
              <Alert
                type="warning"
                showIcon
                style={{ marginBottom: 16 }}
                message="历史项目依据不足"
                description="向量检索未找到足够相似的历史项目。请补充知识库 Engagement 或人工核对对标结论；不会使用演示数据填充。"
              />
            )}

            {matrixRows.length > 0 ? (
              <ComparisonMatrix
                matrixRows={matrixRows}
                projectNames={projectNames}
                projectBaselinesEngagementIds={projectBaselinesEngagementIds}
                editable
                onNewProjectChange={handleNewProjectChange}
              />
            ) : (
              <Alert message="暂无对比矩阵数据" type="warning" />
            )}

            {uncoveredFunctions.length > 0 && (
              <Alert
                type="warning"
                showIcon
                style={{ marginTop: 16 }}
                message="部分工程领域缺少历史参考"
                description={
                  <>
                    以下工程领域在历史资料检索中未找到足够相似项目：
                    <Text strong> {uncoveredFunctions.join("、")}</Text>
                    。请人工补充参考依据，或在「知识库」中补充该类历史项目资料后再确认对标结论。
                  </>
                }
              />
            )}

            <Space style={{ marginTop: 16 }}>
              <Checkbox checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)}>
                我已核对对比表，确认对标结论
              </Checkbox>
              <Button type="primary" loading={saving} onClick={() => void handleSaveReview()}>
                保存修订
              </Button>
              {!isFormalDelivery && (task.status === "in_review" || confirmed) && (
                <Link href={`/proposal?task_id=${task.task_id}`}>
                  <Button type="primary">下一步：方案草案</Button>
                </Link>
              )}
            </Space>
          </Card>
        )}

        {showComparisonMatrix && task.processing_status === "completed" && (
          <Card title="相似项目检索摘要" style={{ marginTop: 16 }}>
            <Table
              rowKey="project_name"
              size="small"
              dataSource={projects}
              pagination={false}
              expandable={{
                expandedRowRender: (row: Record<string, unknown>) => {
                  const dimensions = (row.dimensions as Record<string, Record<string, unknown>>) || {};
                  const dimEntries = Object.entries(dimensions).filter(
                    ([, cell]) => cell && String(cell.value || "") && String(cell.value) !== "未知",
                  );
                  const rowName = String(row.project_name || "");
                  const similarHit = (task.similar_projects || []).find((s) => {
                    const meta = s.metadata as Record<string, unknown> | undefined;
                    return String(meta?.project_name || s.project_name || "") === rowName;
                  });
                  const chunkText = similarHit?.content ? String(similarHit.content).slice(0, 300) : "";
                  const coverage =
                    row.section_coverage ??
                    (similarHit?.metadata as Record<string, unknown> | undefined)?.section_coverage;
                  return (
                    <div style={{ padding: "8px 0" }}>
                      <Paragraph>
                        <Text strong>摘要：</Text>
                        {String(row.summary || "—")}
                      </Paragraph>
                      {coverage != null ? (
                        <Paragraph type="secondary" style={{ marginBottom: 8 }}>
                          章节对齐覆盖率：{Math.round(Number(coverage) * 100)}%
                          {row.same_source ? "（同源文件，已按一致处理）" : ""}
                        </Paragraph>
                      ) : null}
                      {dimEntries.length > 0 ? (
                        <div style={{ marginBottom: 12 }}>
                          <Text strong>维度对齐摘录：</Text>
                          <ul style={{ margin: "8px 0 0", paddingLeft: 20 }}>
                            {dimEntries.slice(0, 8).map(([dimName, cell]) => (
                              <li key={dimName} style={{ marginBottom: 6 }}>
                                <Text strong>{dimName}</Text>
                                {cell.match === true ? (
                                  <Tag
                                    color="success"
                                    style={{ marginLeft: 6 }}
                                  >
                                    {row.same_source || cell.same_source
                                      ? "同源一致"
                                      : "匹配"}
                                  </Tag>
                                ) : cell.match === false ? (
                                  <Tag color="error" style={{ marginLeft: 6 }}>
                                    差异
                                  </Tag>
                                ) : null}
                                <div style={{ color: "rgba(0,0,0,0.65)" }}>
                                  {String(cell.value).slice(0, 200)}
                                  {String(cell.value).length > 200 ? "…" : ""}
                                </div>
                                {cell.section_path ? (
                                  <Text type="secondary" style={{ fontSize: 12 }}>
                                    {String(cell.section_path)}
                                  </Text>
                                ) : null}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : chunkText ? (
                        <Paragraph>
                          <Text strong>检索片段：</Text>
                          {chunkText}
                        </Paragraph>
                      ) : null}
                      <Paragraph type="secondary">
                        来源文档：{String(row.source_doc || "—")} · 实际人天{" "}
                        {String(row.actual_man_days ?? "—")} · 偏差 {String(row.deviation_rate ?? "—")}
                      </Paragraph>
                      {(() => {
                        const eid = resolveEngagementId(row, task.similar_projects);
                        if (!eid) return null;
                        return (
                          <Paragraph style={{ marginBottom: 0 }}>
                            <Link href={buildBaselinesKnowledgeHref(eid)}>
                              查看该项目人天基线
                            </Link>
                          </Paragraph>
                        );
                      })()}
                    </div>
                  );
                },
              }}
              columns={[
                { title: "项目", dataIndex: "project_name" },
                {
                  title: "参考指数",
                  dataIndex: "similarity_score",
                  width: 200,
                  render: (v: number, row: Record<string, unknown>) => {
                    const pct = `${Math.round(Number(v || 0) * 100)}%`;
                    if (row.same_source) {
                      return (
                        <Space size={4} wrap>
                          <Tag color="success">同源 100%</Tag>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            文件内容一致
                          </Text>
                        </Space>
                      );
                    }
                    const vector =
                      row.vector_score != null
                        ? Math.round(Number(row.vector_score) * 100)
                        : null;
                    const structured =
                      row.structured_score != null
                        ? Math.round(Number(row.structured_score) * 100)
                        : null;
                    const coverage =
                      row.section_coverage != null
                        ? Math.round(Number(row.section_coverage) * 100)
                        : null;
                    return (
                      <Space direction="vertical" size={0}>
                        <Text strong>{pct}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {[
                            vector != null ? `召回 ${vector}%` : null,
                            structured != null ? `标签 ${structured}%` : null,
                            coverage != null ? `章节 ${coverage}%` : null,
                          ]
                            .filter(Boolean)
                            .join(" · ") || "综合参考分"}
                        </Text>
                      </Space>
                    );
                  },
                },
                { title: "来源", dataIndex: "source_doc" },
                { title: "摘要", dataIndex: "summary" },
                {
                  title: "人天基线",
                  width: 110,
                  render: (_, row: Record<string, unknown>) => {
                    const eid = resolveEngagementId(row, task?.similar_projects);
                    if (!eid) return "—";
                    return (
                      <Link href={buildBaselinesKnowledgeHref(eid)}>查看</Link>
                    );
                  },
                },
              ]}
            />
            {projects.length > 0 && (
              <Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
                以上对标结果来自平台知识库同一检索引擎 ·{" "}
                <Link href={`/knowledge?q=${encodeURIComponent(buildKnowledgeVerifyQuery(task))}`}>
                  用相同关键词验证
                </Link>
              </Paragraph>
            )}
          </Card>
        )}
      </>
    );
  };

  return (
    <div>
      <input
        ref={uploadInputRef}
        type="file"
        accept=".docx,.doc"
        style={{ display: "none" }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleUpload(file);
          e.target.value = "";
        }}
      />

      <Title level={3}>RFQ 分析</Title>
      {showEmptyUpload && (
        <Paragraph type="secondary" style={{ marginBottom: 8 }}>
          报价助手 · 上传客户 RFQ 文档（<Text strong>.docx / .doc</Text>），解析工程领域（Function）模块、里程碑与交付物，并生成技术维度对比矩阵。
        </Paragraph>
      )}

      <DemoModuleCapability module="rfq" />

      {(task || showProcessing) && (
        <div style={{ marginBottom: showProcessing ? 16 : 28, paddingBottom: 8 }}>
          {showProcessing && task ? (
            <div style={{ marginBottom: 12 }}>
              <Text strong style={{ fontSize: 15 }}>
                {task.file_name}
              </Text>
              <Text type="secondary" style={{ marginLeft: 10, fontSize: 12 }}>
                #{task.task_id.slice(0, 8)}
              </Text>
            </div>
          ) : null}
          <WorkflowSteps
            status={
              task?.artifacts_status ??
              deriveProcessingArtifacts(analysisProgress, task?.processing_status ?? "queued")
            }
            currentPath="/rfq"
          />
        </div>
      )}

      {isLowConfidence && showComparisonMatrix && (
        <Alert
          type="error"
          showIcon
          message="匹配置信度较低"
          description="历史项目相似度不足，请人工核对对比矩阵后再确认进入报价流程。"
          style={{ marginBottom: 24, borderColor: "#E30613" }}
        />
      )}

      <div style={{ minWidth: 0 }}>{renderMainWorkspace()}</div>

      {showEmptyUpload && !uploading && !restoring && showDemoChrome && demoSamples.length > 0 && (
        <Alert
          message="演示样例 RFQ"
          description={
            <>
              可直接下载，或一键试用（自动上传并分析）：
              <List
                size="small"
                style={{ marginTop: 8 }}
                dataSource={demoSamples}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <a key="download" href={item.download_url} download={item.filename}>
                        下载
                      </a>,
                      <Button
                        key="try"
                        type="link"
                        size="small"
                        disabled={uploading}
                        onClick={() => void handleTrySample(item.filename)}
                      >
                        试用此样例
                      </Button>,
                    ]}
                  >
                    <Text strong>{item.title}</Text>
                    <Text type="secondary"> — {item.description}</Text>
                  </List.Item>
                )}
              />
            </>
          }
          type="info"
          showIcon
        />
      )}
    </div>
  );
}
