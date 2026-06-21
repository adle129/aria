"use client";

import { Alert, Space, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { fetchHealth, type HealthData } from "@/api/client";

const { Text } = Typography;

export type DemoModule = "proposal" | "qa" | "quote" | "knowledge";

type CapabilityType = "llm" | "real" | "stub" | "framework";

interface CapabilityItem {
  name: string;
  type: CapabilityType;
  detail: string;
}

const MODULE_CONFIG: Record<DemoModule, { items: CapabilityItem[] }> = {
  proposal: {
    items: [
      {
        name: "生成方案模块",
        type: "stub",
        detail: "固定 Mock 数据，不调用大模型；Phase 2 将接入 RAG + LLM",
      },
    ],
  },
  qa: {
    items: [
      {
        name: "下载 Q_A Excel",
        type: "framework",
        detail: "按需求文档五列导出，不调用大模型（客户 Q_A 模板确认后可切换格式）",
      },
      {
        name: "加载 Mock 示例清单",
        type: "stub",
        detail: "固定 5 条示例问题，不调用大模型；Phase 2 将接入 RAG + LLM 真实生成",
      },
    ],
  },
  quote: {
    items: [
      {
        name: "生成 Excel 人力报价",
        type: "real",
        detail: "基于 RFQ 解析结果与 Mock 人天基线填充 EDAG 模板（PM + Chassis）",
      },
      {
        name: "交付物人天分解表",
        type: "stub",
        detail: "Mock 预览数据，非真实基线核算",
      },
    ],
  },
  knowledge: {
    items: [
      {
        name: "文档检索",
        type: "stub",
        detail: "Mock RAG 模式下为本地模拟检索；真实向量检索需关闭 MOCK_RAG",
      },
    ],
  },
};

function capabilityTag(type: CapabilityType, health: HealthData | null) {
  switch (type) {
    case "llm":
      if (health?.mock_llm) return <Tag>Mock LLM</Tag>;
      if (health?.ollama_reachable && health?.ollama_model_ready) {
        return <Tag color="green">真实 LLM</Tag>;
      }
      return <Tag color="orange">LLM 未就绪</Tag>;
    case "real":
      return <Tag color="green">真实能力</Tag>;
    case "stub":
      return <Tag color="orange">Demo Stub · 无 LLM</Tag>;
    case "framework":
      return <Tag color="blue">框架能力 · 无 LLM</Tag>;
    default:
      return <Tag>—</Tag>;
  }
}

export default function DemoModuleCapability({ module }: { module: DemoModule }) {
  const [health, setHealth] = useState<HealthData | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const items = MODULE_CONFIG[module].items;

  return (
    <Alert
      type="info"
      showIcon
      style={{ marginBottom: 24 }}
      message="本页 Demo 能力说明（与 RFQ 分析页标注方式一致）"
      description={
        <Space direction="vertical" size={8} style={{ width: "100%" }}>
          {items.map((item) => (
            <div key={item.name}>
              <Space wrap size={8}>
                {capabilityTag(item.type, health)}
                <Text strong>{item.name}</Text>
              </Space>
              <div>
                <Text type="secondary">{item.detail}</Text>
              </div>
            </div>
          ))}
          {health && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              当前环境：{health.mock_llm ? "Mock LLM" : `LLM ${health.model}`}
              {health.mock_rag ? " · Mock RAG" : " · 向量检索已启用"}
            </Text>
          )}
        </Space>
      }
    />
  );
}
