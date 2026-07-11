"use client";

import { Steps, Tag } from "antd";
import Link from "next/link";
import type { ArtifactsStatus } from "@/types/task";

const STEP_DEFS = [
  { key: "rfq_parsed", title: "RFQ 解析", href: "/rfq" },
  { key: "comparison_ready", title: "对比矩阵", href: "/rfq" },
  { key: "proposal_ready", title: "方案草案", href: "/proposal" },
  { key: "qa_ready", title: "QA 清单", href: "/qa" },
  { key: "excel_ready", title: "Excel 报价", href: "/quote" },
] as const;

const DEMO_PREVIEW_KEYS = new Set(["proposal_ready", "qa_ready"]);

export default function WorkflowSteps({
  status,
  currentPath,
}: {
  status?: ArtifactsStatus;
  currentPath: string;
}) {
  const flags = status || {
    rfq_parsed: false,
    comparison_ready: false,
    proposal_ready: false,
    qa_ready: false,
    excel_ready: false,
  };

  const currentIndex = STEP_DEFS.findIndex((s) => currentPath.startsWith(s.href));
  const items = STEP_DEFS.map((step, index) => {
    const done = flags[step.key as keyof ArtifactsStatus];
    let stepStatus: "wait" | "process" | "finish" = done ? "finish" : "wait";
    if (index === currentIndex) {
      stepStatus = done ? "finish" : "process";
    }
    return {
      title: <Link href={step.href}>{step.title}</Link>,
      status: stepStatus,
      description: done
        ? DEMO_PREVIEW_KEYS.has(step.key)
          ? "Demo 预览 · 就绪"
          : "就绪"
        : step.key === "proposal_ready" || step.key === "qa_ready"
          ? "Demo 预览"
          : "待完成",
    };
  });

  return (
    <div style={{ marginBottom: 16 }}>
      <Steps size="small" items={items} />
      {!status && (
        <Tag color="default" style={{ marginTop: 8 }}>
          尚未加载任务，请先上传 RFQ 或选择历史任务
        </Tag>
      )}
    </div>
  );
}
