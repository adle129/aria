"use client";

import { CheckOutlined, CloseOutlined } from "@ant-design/icons";
import { Input, Table, Tag, Tooltip } from "antd";
import type { ColumnsType } from "antd/es/table";
import Link from "next/link";
import { buildBaselinesKnowledgeHref } from "@/lib/rfqBaselinesLink";

export interface MatrixHistoryCell {
  project_name?: string;
  similarity_score?: number;
  source_doc?: string;
  value?: string | number;
  match?: boolean | null;
  section_path?: string | null;
  chunk_id?: string | null;
  content_score?: number | null;
}

export interface MatrixRow {
  dimension: string;
  new_project: string | number;
  history: MatrixHistoryCell[];
}

interface ComparisonMatrixProps {
  matrixRows: MatrixRow[];
  projectNames: string[];
  projectBaselinesEngagementIds?: (string | null)[];
  editable?: boolean;
  onNewProjectChange?: (dimension: string, value: string) => void;
}

function MatchIcon({ match }: { match?: boolean | null }) {
  if (match === true) return <CheckOutlined style={{ color: "#52c41a" }} />;
  if (match === false) return <CloseOutlined style={{ color: "#E30613" }} />;
  return <span style={{ color: "#999" }}>—</span>;
}

export function ComparisonMatrix({
  matrixRows,
  projectNames,
  projectBaselinesEngagementIds,
  editable = false,
  onNewProjectChange,
}: ComparisonMatrixProps) {
  const columns: ColumnsType<MatrixRow> = [
    {
      title: "对比维度",
      dataIndex: "dimension",
      fixed: "left",
      width: 140,
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: "新项目需求",
      dataIndex: "new_project",
      width: 160,
      render: (value: string | number, record) => {
        if (!editable || record.dimension.startsWith("技术差异") || record.dimension.includes("偏差")) {
          return value;
        }
        return (
          <Input
            size="small"
            value={String(value)}
            onChange={(e) => onNewProjectChange?.(record.dimension, e.target.value)}
          />
        );
      },
    },
    ...projectNames.map((name, index) => {
      const engagementId = projectBaselinesEngagementIds?.[index] ?? null;
      return {
      title: (
        <div style={{ lineHeight: 1.35 }}>
          <Tooltip title={name}>
            <span>{name.length > 18 ? `${name.slice(0, 18)}…` : name}</span>
          </Tooltip>
          {engagementId ? (
            <div style={{ marginTop: 2 }}>
              <Link
                href={buildBaselinesKnowledgeHref(engagementId)}
                style={{ fontSize: 11, fontWeight: 500 }}
              >
                人天基线
              </Link>
            </div>
          ) : null}
        </div>
      ),
      key: `history_${index}`,
      width: 160,
      render: (_: unknown, record: MatrixRow) => {
        const cell = record.history[index];
        if (!cell) return "—";
        const isSummary = record.dimension === "技术差异总结";
        const showMatch = !isSummary && !record.dimension.includes("人天") && !record.dimension.includes("偏差");
        return (
          <span>
            {showMatch && (
              <>
                <MatchIcon match={cell.match} />{" "}
              </>
            )}
            {cell.section_path ? (
              <Tooltip title={`来源章节：${cell.section_path}`}>
                <span>{cell.value ?? "—"}</span>
              </Tooltip>
            ) : (
              (cell.value ?? "—")
            )}
          </span>
        );
      },
    };
    }),
  ];

  return (
    <Table
      rowKey="dimension"
      size="small"
      pagination={false}
      scroll={{ x: "max-content" }}
      dataSource={matrixRows}
      columns={columns}
    />
  );
}

export function ConfidenceBadge({ level }: { level?: string }) {
  if (!level) return <Tag>未知</Tag>;
  const color = level === "高" ? "green" : level === "中" ? "orange" : "red";
  return (
    <Tag color={color} style={level === "低" ? { borderColor: "#E30613", color: "#E30613" } : undefined}>
      {level}
    </Tag>
  );
}
