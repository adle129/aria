"use client";

import type React from "react";
import { Steps, Typography } from "antd";
import Link from "next/link";
import { useUiProfile } from "@/hooks/useUiProfile";
import { getStepMilestone, isQuotingStepDelivered } from "@/lib/uiProfile";
import type { ArtifactsStatus } from "@/types/task";

const { Text } = Typography;

const ALL_STEP_DEFS = [
  { key: "rfq_parsed", title: "RFQ 解析", href: "/rfq", step: "rfq" as const },
  { key: "comparison_ready", title: "对比矩阵", href: "/rfq", step: "rfq" as const },
  { key: "proposal_ready", title: "方案草案", href: "/proposal", step: "proposal" as const },
  { key: "qa_ready", title: "QA 清单", href: "/qa", step: "qa" as const },
  { key: "excel_ready", title: "Excel 报价", href: "/quote", step: "quote" as const },
] as const;

const DEMO_PREVIEW_KEYS = new Set(["proposal_ready", "qa_ready"]);

export default function WorkflowSteps({
  status,
  currentPath,
}: {
  status?: ArtifactsStatus;
  currentPath: string;
}) {
  const { profile, showDemoChrome } = useUiProfile();

  const flags = status || {
    rfq_parsed: false,
    comparison_ready: false,
    proposal_ready: false,
    qa_ready: false,
    excel_ready: false,
  };

  const currentIndex = ALL_STEP_DEFS.findIndex((s) => currentPath.startsWith(s.href));

  const items = ALL_STEP_DEFS.map((stepDef, index) => {
    const delivered = isQuotingStepDelivered(profile, stepDef.step);

    if (!delivered) {
      const milestone = getStepMilestone(stepDef.step);
      return {
        title: <span style={{ color: "#bfbfbf" }}>{stepDef.title}</span>,
        status: "wait" as const,
        description: (
          <span style={{ color: "#d9d9d9", fontSize: 11 }}>
            {milestone ? `待开通 · ${milestone}` : "待开通"}
          </span>
        ),
      };
    }

    const done = flags[stepDef.key as keyof ArtifactsStatus];
    let stepStatus: "wait" | "process" | "finish" = done ? "finish" : "wait";
    if (index === currentIndex) {
      stepStatus = done ? "finish" : "process";
    }

    let description: React.ReactNode = done ? "就绪" : "待完成";
    if (showDemoChrome && !done && DEMO_PREVIEW_KEYS.has(stepDef.key)) {
      description = "Demo 预览";
    } else if (showDemoChrome && done && DEMO_PREVIEW_KEYS.has(stepDef.key)) {
      description = "Demo 预览 · 就绪";
    }

    return {
      title: <Link href={stepDef.href}>{stepDef.title}</Link>,
      status: stepStatus,
      description,
    };
  });

  return (
    <div style={{ marginBottom: 0 }}>
      <Steps size="small" items={items} />
      {!status && (
        <Text type="secondary" style={{ display: "block", marginTop: 8, fontSize: 12 }}>
          尚未加载任务 — 请上传 RFQ 或从左侧选择历史任务
        </Text>
      )}
    </div>
  );
}
