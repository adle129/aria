"use client";

import { Alert, Collapse, Descriptions, List, Table } from "antd";
import type { TaskPayload } from "@/types/task";

interface RfqParseSummaryProps {
  task: TaskPayload;
  defaultExpanded?: boolean;
}

export default function RfqParseSummary({ task, defaultExpanded = false }: RfqParseSummaryProps) {
  const mods = task.rfq_modules as Record<string, unknown> | undefined;
  if (!mods) return null;

  const modules = (mods.modules as Array<Record<string, unknown>>) || [];
  const milestones = (mods.milestones as Record<string, string>) || {};
  const specialReqs = (mods.special_requirements as string[]) || [];
  const allDeliverables = [...new Set(modules.flatMap((m) => (m.deliverables as string[]) || []))];

  return (
    <Collapse
      style={{ marginBottom: 20, background: "transparent", border: "none" }}
      bordered={false}
      defaultActiveKey={defaultExpanded ? ["parse"] : []}
      items={[
        {
          key: "parse",
          label: <span style={{ fontWeight: 500 }}>RFQ 解析结果</span>,
          style: { borderBottom: "1px solid #F0F0F0", background: "transparent" },
          children: (
            <>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="项目">
                  {String(mods.project_name || "—")}
                </Descriptions.Item>
                <Descriptions.Item label="客户">
                  {String(mods.customer || "—")}
                </Descriptions.Item>
                <Descriptions.Item label="平台">
                  {String(mods.platform_type || "—")}
                </Descriptions.Item>
                <Descriptions.Item label="周期">
                  {String(mods.timeline_months || "—")} 月
                </Descriptions.Item>
              </Descriptions>

              {Object.keys(milestones).length > 0 && (
                <Descriptions column={3} size="small" title="里程碑" style={{ marginTop: 16 }}>
                  {Object.entries(milestones).map(([k, v]) => (
                    <Descriptions.Item key={k} label={k}>
                      {v}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              )}

              <Table
                style={{ marginTop: 16 }}
                rowKey={(_, i) => String(i)}
                size="small"
                pagination={false}
                dataSource={modules}
                columns={[
                  { title: "工程领域", dataIndex: "function" },
                  { title: "模块", dataIndex: "module_name" },
                  { title: "复杂度", dataIndex: "estimated_complexity" },
                  {
                    title: "交付物",
                    dataIndex: "deliverables",
                    render: (items: string[]) => (items || []).join("；") || "—",
                  },
                ]}
              />

              {allDeliverables.length > 0 && (
                <Collapse
                  style={{ marginTop: 16 }}
                  items={[
                    {
                      key: "deliverables",
                      label: `全部交付物（${allDeliverables.length} 项）`,
                      children: (
                        <List
                          size="small"
                          dataSource={allDeliverables}
                          renderItem={(item) => <List.Item>{item}</List.Item>}
                        />
                      ),
                    },
                  ]}
                />
              )}

              {specialReqs.length > 0 && (
                <Alert
                  style={{ marginTop: 16 }}
                  type="info"
                  message="特殊要求 / 假设"
                  description={
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                      {specialReqs.map((r) => (
                        <li key={r}>{r}</li>
                      ))}
                    </ul>
                  }
                />
              )}
            </>
          ),
        },
      ]}
    />
  );
}
