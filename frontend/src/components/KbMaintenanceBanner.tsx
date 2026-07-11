"use client";

import { Alert } from "antd";
import { useEffect, useState } from "react";
import { apiClient } from "@/api/client";
import { INDEX_JOB_PHASE_LABEL } from "@/lib/knowledgeIndexJob";

export default function KbMaintenanceBanner() {
  const [visible, setVisible] = useState(false);
  const [phase, setPhase] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const resp = await apiClient.get<{
          code: number;
          data: { active?: boolean; phase?: string | null };
        }>("/knowledge/maintenance", { silentError: true });
        if (cancelled) return;
        const data = resp.data.data;
        setVisible(Boolean(data?.active));
        setPhase(data?.phase ?? null);
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

  const phaseLabel = phase
    ? INDEX_JOB_PHASE_LABEL[phase] ?? phase
    : null;

  return (
    <Alert
      type="info"
      showIcon
      banner
      message="知识库正在后台更新索引"
      description={
        phaseLabel
          ? `当前阶段：${phaseLabel}。检索与 RFQ 对标仍使用上一版稳定索引，无需等待。`
          : "检索与 RFQ 对标仍使用上一版稳定索引，无需等待。"
      }
    />
  );
}
