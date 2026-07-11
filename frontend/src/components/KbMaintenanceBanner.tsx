"use client";

import { Alert } from "antd";
import { useEffect, useState } from "react";
import { apiClient } from "@/api/client";
import { ACTIVE_INDEX_JOB_STATUSES } from "@/lib/knowledgeIndexJob";

export default function KbMaintenanceBanner() {
  const [visible, setVisible] = useState(false);
  const [phase, setPhase] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const resp = await apiClient.get<{
          code: number;
          data: { status?: string; phase?: string | null } | null;
        }>("/knowledge/imports/active");
        const job = resp.data.data;
        if (cancelled) return;
        const active =
          job != null && ACTIVE_INDEX_JOB_STATUSES.has(job.status as never);
        setVisible(active);
        setPhase(job?.phase ?? null);
      } catch {
        if (!cancelled) setVisible(false);
      }
    };
    void load();
    const timer = window.setInterval(() => void load(), 15000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  if (!visible) return null;

  return (
    <Alert
      type="info"
      showIcon
      banner
      message="知识库正在后台更新索引"
      description={
        phase
          ? `当前阶段：${phase}。检索与 RFQ 对标仍使用上一版稳定索引，无需等待。`
          : "检索与 RFQ 对标仍使用上一版稳定索引，无需等待。"
      }
    />
  );
}
