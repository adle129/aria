"use client";

import { Button, Card, Checkbox, Table, Tag, Tooltip, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  QUOTE_FUNCTION_KEYS,
  QUOTE_FUNCTION_SHORT,
  applyEngagementToInScope,
  countMappedInScope,
  formatSimilarityPercent,
  isColumnFullySelected,
  toggleColumnForInScope,
  truncateProjectLabel,
  type FunctionSourceMap,
  type QuoteFunctionKey,
  type SourceCandidate,
} from "@/lib/functionSourceMap";
import { formatProjectIdLine } from "@/lib/projectIdentity";

const { Text } = Typography;

/** engagementId -> Function keys that have manpower baselines */
export type BaselineAvailability = Record<string, Set<string> | string[]>;

interface FunctionSourcePickerProps {
  value: FunctionSourceMap;
  inScope: QuoteFunctionKey[];
  candidates: SourceCandidate[];
  baselineAvailability?: BaselineAvailability;
  saving?: boolean;
  disabled?: boolean;
  onChange: (next: FunctionSourceMap) => void;
  onSave: () => void;
}

type Row = {
  key: QuoteFunctionKey;
  inScope: boolean;
};

function hasBaseline(
  availability: BaselineAvailability | undefined,
  engagementId: string,
  functionKey: string,
): boolean {
  if (!availability || Object.keys(availability).length === 0) return true;
  const entry = availability[engagementId];
  if (entry === undefined) return true;
  if (entry instanceof Set) return entry.has(functionKey);
  return entry.includes(functionKey);
}

function projectColumnTitle(
  c: SourceCandidate,
  columnFullySelected: boolean,
  onToggleColumn: (() => void) | null,
  disabled: boolean,
) {
  const pct = formatSimilarityPercent(c.similarityScore);
  const idLine = formatProjectIdLine(c.engagementId);
  const tip = [
    c.projectName,
    c.customer,
    c.vehicleModel,
    idLine,
    pct ? `相似度 ${pct}` : null,
    c.engagementId ? null : "未关联入库项目，不可选为报价来源",
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div style={{ lineHeight: 1.35, minWidth: 120 }}>
      <Tooltip title={tip}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 13 }}>
            {truncateProjectLabel(c.projectName, 16)}
          </div>
          <div style={{ fontSize: 11, color: "#8c8c8c", marginTop: 2 }}>
            {truncateProjectLabel(c.customer || "—", 12)} ·{" "}
            {truncateProjectLabel(c.vehicleModel || "—", 12)}
          </div>
          {idLine ? (
            <div style={{ fontSize: 11, color: "#bfbfbf", marginTop: 2 }}>
              {truncateProjectLabel(idLine, 22)}
            </div>
          ) : null}
          {pct ? (
            <div style={{ fontSize: 11, color: "#8c8c8c", marginTop: 2 }}>相似 {pct}</div>
          ) : null}
        </div>
      </Tooltip>
      {onToggleColumn ? (
        <Button
          type="link"
          size="small"
          disabled={disabled || !c.engagementId}
          style={{ padding: 0, height: "auto", fontSize: 11, marginTop: 2 }}
          onClick={onToggleColumn}
        >
          {columnFullySelected ? "本列全不选" : "本列全选"}
        </Button>
      ) : (
        <Text type="secondary" style={{ fontSize: 11, display: "block", marginTop: 2 }}>
          无法选源
        </Text>
      )}
    </div>
  );
}

export function FunctionSourcePicker({
  value,
  inScope,
  candidates,
  baselineAvailability,
  saving = false,
  disabled = false,
  onChange,
  onSave,
}: FunctionSourcePickerProps) {
  const inScopeSet = new Set(inScope);
  const { mapped, total } = countMappedInScope(value, inScope);
  const selectableCount = candidates.filter((c) => c.engagementId).length;

  const dataSource: Row[] = QUOTE_FUNCTION_KEYS.map((key) => ({
    key,
    inScope: inScopeSet.has(key),
  }));

  const setModuleSource = (moduleKey: QuoteFunctionKey, engagementId: string | null) => {
    onChange({
      ...value,
      [moduleKey]: engagementId,
    });
  };

  const columns: ColumnsType<Row> = [
    {
      title: "报价模块",
      dataIndex: "key",
      fixed: "left",
      width: 128,
      render: (key: QuoteFunctionKey, row) => (
        <div>
          <Text strong style={{ fontSize: 13 }}>
            {QUOTE_FUNCTION_SHORT[key]}
          </Text>
          {!row.inScope ? (
            <div>
              <Text type="secondary" style={{ fontSize: 11 }}>
                不在范围
              </Text>
            </div>
          ) : null}
        </div>
      ),
    },
    ...candidates.map((c) => ({
      title: projectColumnTitle(
        c,
        Boolean(
          c.engagementId && isColumnFullySelected(value, inScope, c.engagementId),
        ),
        c.engagementId
          ? () => onChange(toggleColumnForInScope(value, inScope, c.engagementId!))
          : null,
        disabled,
      ),
      key: c.columnKey,
      align: "center" as const,
      width: 168,
      render: (_: unknown, row: Row) => {
        if (!row.inScope) {
          return <Text type="secondary">—</Text>;
        }
        if (!c.engagementId) {
          return (
            <Tooltip title="该历史列未关联入库项目，无法作为报价来源">
              <Checkbox disabled checked={false} />
            </Tooltip>
          );
        }
        const ok = hasBaseline(baselineAvailability, c.engagementId, row.key);
        const checked = value[row.key] === c.engagementId;
        return (
          <Tooltip
            title={
              !ok
                ? "该历史项目无此模块报价基线"
                : checked
                  ? "取消勾选 = 本模块不引用历史"
                  : `采用「${c.projectName}」的 ${QUOTE_FUNCTION_SHORT[row.key]}`
            }
          >
            <Checkbox
              checked={checked}
              disabled={disabled || !ok}
              onChange={(e) => {
                if (e.target.checked) {
                  setModuleSource(row.key, c.engagementId);
                } else if (checked) {
                  setModuleSource(row.key, null);
                }
              }}
            />
          </Tooltip>
        );
      },
    })),
  ];

  return (
    <Card
      size="small"
      title={
        <span>
          报价数据源
          <Text type="secondary" style={{ fontWeight: 400, marginLeft: 8, fontSize: 13 }}>
            与上方历史项目列对齐 · 勾选采用该项目模块
          </Text>
        </span>
      }
      style={{ marginTop: 16 }}
      extra={
        <Button type="primary" size="small" loading={saving} disabled={disabled} onClick={onSave}>
          保存
        </Button>
      }
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 8,
          alignItems: "center",
          marginBottom: 10,
        }}
      >
        <Text type="secondary" style={{ fontSize: 12 }}>
          表格列与「技术维度对比矩阵」历史项目一致。每行最多勾选一个项目；不勾选表示该模块不引用。此处仅保存选源意向；按多源真正拼装 Excel
          属后续里程碑（签约后 / M3）。
        </Text>
        <Tag style={{ marginInlineEnd: 0 }}>
          已选用 {mapped}/{total}
        </Tag>
        {candidates.length > 0 && selectableCount < candidates.length ? (
          <Tag color="orange">部分历史列未入库关联，仅可勾选有项目 ID 的列</Tag>
        ) : null}
        <Button
          type="link"
          size="small"
          disabled={disabled || total === 0}
          style={{ padding: 0, height: "auto", fontSize: 12 }}
          onClick={() => onChange(applyEngagementToInScope(value, inScope, null))}
        >
          清空全部勾选
        </Button>
      </div>

      {candidates.length === 0 ? (
        <Text type="warning">暂无历史对比项目列。请先完成对标检索生成对比矩阵。</Text>
      ) : (
        <Table<Row>
          size="small"
          pagination={false}
          rowKey="key"
          dataSource={dataSource}
          columns={columns}
          scroll={{ x: "max-content" }}
          onRow={(row) =>
            row.inScope
              ? {}
              : { style: { background: "#fafafa", color: "rgba(0,0,0,0.45)" } }
          }
        />
      )}
    </Card>
  );
}
