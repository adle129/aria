"use client";

import { CheckCircleFilled, LoadingOutlined } from "@ant-design/icons";
import { Progress, Typography } from "antd";

const { Text, Title } = Typography;

export const RFQ_PROCESSING_STEPS = [
  { key: "upload", label: "文件上传" },
  { key: "parse", label: "解析 RFQ 文档" },
  { key: "dimension", label: "匹配基准维度库" },
  { key: "review", label: "等待工程师确认" },
] as const;

export type ProcessingStepState = "done" | "active" | "pending";

export function isQueueWaiting(
  processingStatus: string,
  queuePosition?: number | null,
): boolean {
  return (
    (processingStatus === "queued" || processingStatus === "pending") &&
    queuePosition != null &&
    queuePosition > 0
  );
}

export function resolveProcessingStepIndex(processingStatus: string, progress: number): number {
  switch (processingStatus) {
    case "queued":
    case "pending":
      return 1;
    case "parsing":
      return progress >= 35 ? 2 : 1;
    case "dimension_review":
      return 3;
    case "retrieving":
    case "generating":
      return 3;
    default:
      return 1;
  }
}

/** Step visuals for the checklist; queued tasks show upload done + queue wait. */
export function resolveProcessingStepVisuals(
  processingStatus: string,
  progress: number,
  queuePosition?: number | null,
): Array<{ label: string; state: ProcessingStepState }> {
  if (isQueueWaiting(processingStatus, queuePosition)) {
    return [
      { label: RFQ_PROCESSING_STEPS[0].label, state: "done" },
      { label: "排队等待", state: "active" },
      { label: RFQ_PROCESSING_STEPS[1].label, state: "pending" },
      { label: RFQ_PROCESSING_STEPS[2].label, state: "pending" },
      { label: RFQ_PROCESSING_STEPS[3].label, state: "pending" },
    ];
  }

  const activeIndex = resolveProcessingStepIndex(processingStatus, progress);
  return RFQ_PROCESSING_STEPS.map((step, index) => {
    if (index < activeIndex) return { label: step.label, state: "done" as const };
    if (index === activeIndex) return { label: step.label, state: "active" as const };
    return { label: step.label, state: "pending" as const };
  });
}

interface RfqAnalysisProgressProps {
  progress: number;
  message: string;
  processingStatus: string;
  queuePosition?: number | null;
  estimatedWaitSeconds?: number | null;
  useRealLlm?: boolean | null;
  stalled?: boolean;
  onResumePolling?: () => void;
}

export default function RfqAnalysisProgress({
  progress,
  message,
  processingStatus,
  queuePosition,
  estimatedWaitSeconds,
  useRealLlm,
  stalled,
  onResumePolling,
}: RfqAnalysisProgressProps) {
  const waitHint =
    queuePosition != null && queuePosition > 0
      ? `排队中：第 ${queuePosition} 位${
          estimatedWaitSeconds != null && estimatedWaitSeconds > 0
            ? ` · 预计约 ${Math.ceil(estimatedWaitSeconds / 60)} 分钟`
            : ""
        }`
      : stalled
        ? "后台仍在处理，可继续等待或稍后从左侧任务列表打开"
        : useRealLlm
          ? "本地模型分析中，通常需要 1–3 分钟，请稍候"
          : "正在处理，请稍候";

  const stepVisuals = resolveProcessingStepVisuals(processingStatus, progress, queuePosition);

  return (
    <div
      style={{
        maxWidth: 440,
        margin: "48px auto",
        textAlign: "center",
        padding: "8px 16px 24px",
      }}
    >
      <Title level={4} style={{ marginBottom: 8, fontWeight: 500 }}>
        {message || "正在分析 RFQ…"}
      </Title>
      <Text type="secondary" style={{ display: "block", marginBottom: 28, fontSize: 13 }}>
        {waitHint}
      </Text>
      <Progress
        percent={progress}
        status={stalled ? "exception" : progress === 100 ? "success" : "active"}
        strokeColor={stalled ? "#E30613" : progress < 100 ? "#8C8C8C" : undefined}
        trailColor="#F0F0F0"
        showInfo
        style={{ maxWidth: 360, margin: "0 auto 28px" }}
      />
      <div
        style={{
          textAlign: "left",
          maxWidth: 300,
          margin: "0 auto",
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        {stepVisuals.map((step) => {
          const done = step.state === "done";
          const active = step.state === "active";
          return (
            <div
              key={step.label}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                color: done ? "#3D7A5A" : active ? "#333333" : "#BFBFBF",
                fontSize: 13,
              }}
            >
              {done ? (
                <CheckCircleFilled style={{ fontSize: 14 }} />
              ) : active ? (
                <LoadingOutlined spin style={{ fontSize: 14 }} />
              ) : (
                <span
                  style={{
                    width: 14,
                    height: 14,
                    borderRadius: "50%",
                    border: "1.5px solid #D9D9D9",
                    display: "inline-block",
                    flexShrink: 0,
                  }}
                />
              )}
              <span style={{ fontWeight: active ? 500 : 400 }}>{step.label}</span>
            </div>
          );
        })}
      </div>
      {stalled && onResumePolling ? (
        <div style={{ marginTop: 24 }}>
          <button
            type="button"
            onClick={onResumePolling}
            style={{
              border: "1px solid #D9D9D9",
              background: "#FFFFFF",
              borderRadius: 4,
              padding: "6px 16px",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            继续等待
          </button>
        </div>
      ) : null}
    </div>
  );
}
