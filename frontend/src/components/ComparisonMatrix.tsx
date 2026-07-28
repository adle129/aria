"use client";

import { CheckOutlined, CloseOutlined } from "@ant-design/icons";
import { Input, Table, Tag, Tooltip, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  formatMatrixHeaderTooltip,
  truncateHeaderText,
  type MatrixProjectHeader,
} from "@/lib/matrixProjectHeader";
import { formatProjectIdLine } from "@/lib/projectIdentity";

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
  /** @deprecated prefer projectHeaders (R1-CHG02) */
  projectNames?: string[];
  projectHeaders?: MatrixProjectHeader[];
  projectBaselinesEngagementIds?: (string | null)[];
  editable?: boolean;
  onNewProjectChange?: (dimension: string, value: string) => void;
  /** Open in-page baselines drawer (R1-CHG01); do not link to /knowledge. */
  onOpenBaselines?: (engagementId: string) => void;
  /** Download historical source file (R1-CHG06); default RFQ. */
  onDownloadSource?: (engagementId: string, docType?: string) => void;
}

function MatchIcon({ match }: { match?: boolean | null }) {
  if (match === true) return <CheckOutlined style={{ color: "#52c41a" }} />;
  if (match === false) return <CloseOutlined style={{ color: "#E30613" }} />;
  return <span style={{ color: "#999" }}>—</span>;
}

export function ComparisonMatrix({
  matrixRows,
  projectNames,
  projectHeaders,
  projectBaselinesEngagementIds,
  editable = false,
  onNewProjectChange,
  onOpenBaselines,
  onDownloadSource,
}: ComparisonMatrixProps) {
  const headers: MatrixProjectHeader[] =
    projectHeaders && projectHeaders.length > 0
      ? projectHeaders
      : (projectNames || []).map((name) => ({
          project_name: name,
          customer: "—",
          vehicle_model: "—",
          engagement_id: null,
        }));

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
    ...headers.map((header, index) => {
      const engagementId =
        header.engagement_id || projectBaselinesEngagementIds?.[index] || null;
      const tip = formatMatrixHeaderTooltip({
        ...header,
        engagement_id: engagementId,
      });
      const idLine = formatProjectIdLine(engagementId);
      return {
      title: (
        <div style={{ lineHeight: 1.35 }}>
          <Tooltip title={<span style={{ whiteSpace: "pre-line" }}>{tip}</span>}>
            <div>
              <div style={{ fontWeight: 600 }}>
                {truncateHeaderText(header.project_name, 16)}
              </div>
              <div style={{ fontSize: 11, fontWeight: 400, color: "#8c8c8c", marginTop: 2 }}>
                {truncateHeaderText(header.customer, 12)} ·{" "}
                {truncateHeaderText(header.vehicle_model, 12)}
              </div>
              {idLine ? (
                <div style={{ fontSize: 11, fontWeight: 400, color: "#bfbfbf", marginTop: 2 }}>
                  {truncateHeaderText(idLine, 22)}
                </div>
              ) : null}
            </div>
          </Tooltip>
          {engagementId && (onOpenBaselines || onDownloadSource) ? (
            <div style={{ marginTop: 2 }}>
              {onOpenBaselines ? (
                <Typography.Link
                  style={{ fontSize: 11, fontWeight: 500, marginRight: 8 }}
                  onClick={(e) => {
                    e.preventDefault();
                    onOpenBaselines(engagementId);
                  }}
                >
                  人天明细
                </Typography.Link>
              ) : null}
              {onDownloadSource ? (
                <Typography.Link
                  style={{ fontSize: 11, fontWeight: 500 }}
                  onClick={(e) => {
                    e.preventDefault();
                    onDownloadSource(engagementId, "rfq");
                  }}
                >
                  下载 RFQ
                </Typography.Link>
              ) : null}
            </div>
          ) : null}
        </div>
      ),
      key: `history_${index}`,
      width: 168,
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
