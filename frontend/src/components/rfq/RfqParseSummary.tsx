"use client";

import { InfoCircleOutlined } from "@ant-design/icons";
import {
  Alert,
  Collapse,
  Descriptions,
  List,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import type { TaskPayload } from "@/types/task";
import { buildMilestoneGroupViews } from "@/lib/rfqMilestoneGroups";
import {
  computeModuleQualityStats,
  countDeliverableItems,
  isUnassessedComplexity,
  isUnknownFunction,
  normalizeDeliverableGroups,
  resolveWorkSections,
  workSectionCategoryLabel,
  type DeliverableGroup,
  type RfqModuleRow,
  type WorkSection,
} from "@/lib/rfqModuleGroups";
import { formatFunctionLabel } from "@/lib/functionLabels";

const { Text } = Typography;

interface RfqParseSummaryProps {
  task: TaskPayload;
  defaultExpanded?: boolean;
}

function workItemColumns(): ColumnsType<RfqModuleRow> {
  return [
    {
      title: "工程领域",
      dataIndex: "function",
      width: 140,
      render: (value: string | undefined) => {
        if (isUnknownFunction(value)) {
          return <Tag color="warning">待确认</Tag>;
        }
        return formatFunctionLabel(value);
      },
    },
    {
      title: "工作条目",
      dataIndex: "module_name",
      render: (value: string | undefined, row) => {
        const title = value || "—";
        const detail =
          row.description && row.description !== title ? row.description : null;
        return (
          <div>
            <Text style={{ whiteSpace: "normal", wordBreak: "break-word" }}>{title}</Text>
            {detail ? (
              <div>
                <Text type="secondary" style={{ fontSize: 12, whiteSpace: "normal", wordBreak: "break-word" }}>
                  {detail}
                </Text>
              </div>
            ) : null}
            {row.section_path ? (
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {row.section_path}
                </Text>
              </div>
            ) : null}
          </div>
        );
      },
    },
    {
      title: "复杂度",
      dataIndex: "estimated_complexity",
      width: 100,
      render: (value: string | undefined) =>
        isUnassessedComplexity(value) ? (
          <Text type="secondary">未评估</Text>
        ) : (
          value || "—"
        ),
    },
  ];
}

function clauseColumns(): ColumnsType<RfqModuleRow> {
  return [
    {
      title: "条目",
      dataIndex: "module_name",
      render: (value: string | undefined) => (
        <Text style={{ whiteSpace: "normal", wordBreak: "break-word" }}>{value || "—"}</Text>
      ),
    },
  ];
}

function WorkSectionBlock({ section }: { section: WorkSection }) {
  const hasCategories = section.categories.some((c) => c.key !== "_all" && c.label);
  const columns = hasCategories || section.kind === "work_content" ? workItemColumns() : clauseColumns();
  const defaultKeys = section.categories.slice(0, hasCategories ? 4 : 1).map((c) => c.key);

  return (
    <div style={{ marginTop: 16 }}>
      <Space size={6} style={{ marginBottom: 8 }}>
        <Text strong>{section.title}</Text>
        <Tooltip title="二级目录为表格标题，三级目录为分类；均来自 RFQ 章节路径原文。">
          <InfoCircleOutlined style={{ color: "#999", fontSize: 12 }} />
        </Tooltip>
        <Tag>
          {section.categories.reduce((n, c) => n + c.rows.length, 0)} 项
        </Tag>
      </Space>

      {hasCategories ? (
        <Collapse
          size="small"
          defaultActiveKey={defaultKeys}
          items={section.categories.map((group) => ({
            key: group.key,
            label: (
              <Space size={8}>
                <span>{workSectionCategoryLabel(group)}</span>
                {group.function &&
                workSectionCategoryLabel(group) !==
                  formatFunctionLabel(String(group.function)) ? (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {formatFunctionLabel(String(group.function))}
                  </Text>
                ) : null}
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {group.rows.length} 项
                </Text>
              </Space>
            ),
            children: (
              <Table
                size="small"
                pagination={false}
                rowKey={(row, index) =>
                  `${row.section_id || row.module_name || "row"}-${index}`
                }
                dataSource={group.rows}
                columns={columns}
              />
            ),
          }))}
        />
      ) : (
        <Table
          size="small"
          pagination={false}
          rowKey={(row, index) => `${row.section_id || row.module_name || "row"}-${index}`}
          dataSource={section.categories.flatMap((c) => c.rows)}
          columns={clauseColumns()}
        />
      )}
    </div>
  );
}

export default function RfqParseSummary({ task, defaultExpanded = false }: RfqParseSummaryProps) {
  const mods = task.rfq_modules as Record<string, unknown> | undefined;
  if (!mods) return null;

  const modules = (mods.modules as RfqModuleRow[]) || [];
  const workSections = resolveWorkSections(
    mods.work_sections as WorkSection[] | undefined,
    modules,
  );
  const deliverableGroups = normalizeDeliverableGroups(
    mods.deliverable_groups as DeliverableGroup[] | undefined,
  );
  const deliverableTotal = countDeliverableItems(deliverableGroups);
  const milestones = (mods.milestones as Record<string, string>) || {};
  const milestoneGroups = mods.milestone_groups as
    | {
        acceptance?: Record<string, string>;
        data?: Record<string, string>;
        other?: Record<string, string>;
      }
    | undefined;
  const milestoneViews = buildMilestoneGroupViews(milestones, milestoneGroups);
  const specialReqs = (mods.special_requirements as string[]) || [];
  const quality = computeModuleQualityStats(modules);
  const showQualityWarning = quality.manyUnknownFunctions;
  const expandParse =
    defaultExpanded || showQualityWarning || task.processing_status === "dimension_review";

  return (
    <Collapse
      style={{ marginTop: 16 }}
      defaultActiveKey={expandParse ? ["parse"] : []}
      items={[
        {
          key: "parse",
          label: (
            <Space size={8}>
              <span>RFQ 解析摘要</span>
              <Tag>{modules.length} 工作项</Tag>
              {deliverableTotal > 0 ? <Tag>{deliverableTotal} 交付物</Tag> : null}
            </Space>
          ),
          children: (
            <>
              {milestoneViews.length > 0 && (
                <div>
                  {milestoneViews.map((group) => (
                    <div key={group.kind} style={{ marginBottom: 12 }}>
                      <Text strong>{group.title}</Text>
                      <Descriptions size="small" column={2} style={{ marginTop: 8 }}>
                        {group.entries.map((entry) => (
                          <Descriptions.Item
                            key={`${group.kind}-${entry.key}`}
                            label={entry.key}
                          >
                            {entry.date}
                          </Descriptions.Item>
                        ))}
                      </Descriptions>
                    </div>
                  ))}
                </div>
              )}

              {workSections.length > 0 && (
                <div style={{ marginTop: milestoneViews.length > 0 ? 0 : 0 }}>
                  <Space wrap size={[8, 8]} style={{ marginBottom: 8 }}>
                    <Tag>工作条目 {quality.total}</Tag>
                    <Tag color={quality.manyUnknownFunctions ? "warning" : "default"}>
                      领域已识别 {quality.knownFunction}
                      {quality.unknownFunction > 0 ? `（待确认 ${quality.unknownFunction}）` : ""}
                    </Tag>
                    <Tag>
                      复杂度未评估 {quality.unassessedComplexity}/{quality.total}
                    </Tag>
                  </Space>

                  {showQualityWarning ? (
                    <Alert
                      style={{ marginBottom: 12 }}
                      type="warning"
                      showIcon
                      message="工作内容待核对"
                      description="部分工作条目未能识别工程领域（已标为待确认）。请在维度复核中核对。"
                    />
                  ) : null}

                  {workSections.map((section) => (
                    <WorkSectionBlock key={`${section.kind}-${section.title}`} section={section} />
                  ))}
                </div>
              )}

              {deliverableGroups.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <Space size={6} style={{ marginBottom: 8 }}>
                    <Text strong>已解析交付物汇总</Text>
                    <Tooltip title="按 RFQ 交付物表题（如「整车总布置交付物」）分类；与上方工作内容分表展示。">
                      <InfoCircleOutlined style={{ color: "#999", fontSize: 12 }} />
                    </Tooltip>
                    <Tag>
                      {deliverableTotal} 项 · {deliverableGroups.length} 类
                    </Tag>
                  </Space>
                  <Collapse
                    size="small"
                    defaultActiveKey={deliverableGroups.slice(0, 3).map((g) => g.category)}
                    items={deliverableGroups.map((group) => ({
                      key: group.category,
                      label: (
                        <Space size={8}>
                          <span>{group.category}</span>
                          {group.function ? (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {formatFunctionLabel(group.function)}
                            </Text>
                          ) : null}
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {group.items.length} 项
                          </Text>
                        </Space>
                      ),
                      children: (
                        <List
                          size="small"
                          dataSource={group.items}
                          renderItem={(item) => <List.Item>{item}</List.Item>}
                        />
                      ),
                    }))}
                  />
                </div>
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
