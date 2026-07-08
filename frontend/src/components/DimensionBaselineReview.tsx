"use client";

import {
  computeReviewSummary,
  formatModuleStatusLabel,
  inferMatchMeta,
  inferReviewTier,
  matchTypeTagColor,
  moduleMatchesFilter,
  modulesWithInScope,
  countModulesForFilter,
  needsReviewItems,
  resolveEvidenceDisplay,
  type ReviewSummary,
} from "@/lib/dimensionReview";
import {
  Alert,
  Button,
  Checkbox,
  Collapse,
  Descriptions,
  Drawer,
  Input,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { useMemo, useState, type CSSProperties } from "react";

const { Text } = Typography;

const STICKY_TOOLBAR_STYLE: CSSProperties = {
  position: "sticky",
  top: 0,
  zIndex: 20,
  background: "#fff",
  padding: "12px 0",
  marginBottom: 16,
  borderBottom: "1px solid #f0f0f0",
  boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
};

const STICKY_FOOTER_STYLE: CSSProperties = {
  position: "sticky",
  bottom: 0,
  zIndex: 20,
  background: "#fff",
  padding: "12px 0",
  marginTop: 16,
  borderTop: "1px solid #f0f0f0",
  boxShadow: "0 -2px 8px rgba(0,0,0,0.04)",
};

export interface DimensionEvidence {
  rfq_section?: string;
  rfq_section_title?: string;
  matched_keyword?: string;
  snippet?: string;
  source_ref?: string;
}

export interface DimensionDraftItem {
  dimension_id: string;
  module?: string;
  module_label?: string;
  name: string;
  in_scope: boolean;
  work_content?: string;
  source_ref?: string | null;
  source_label?: string;
  match_type?: string;
  review_tier?: "auto_include" | "needs_review" | "auto_exclude";
  evidence?: DimensionEvidence;
  manually_adjusted?: boolean;
  custom?: boolean;
  confidence?: string;
}

export interface DimensionDraftModuleSummary {
  module: string;
  module_label?: string;
  needed: boolean;
  in_scope_count: number;
  needs_review_count?: number;
}

export interface DimensionDraft {
  baseline_version?: string;
  items: DimensionDraftItem[];
  custom_items?: DimensionDraftItem[];
  module_summary?: DimensionDraftModuleSummary[];
  review_summary?: ReviewSummary;
}

interface DimensionBaselineReviewProps {
  draft: DimensionDraft;
  saving?: boolean;
  confirming?: boolean;
  onDraftChange: (draft: DimensionDraft) => void;
  onSaveDraft: () => void;
  onConfirm: () => void;
}

function recomputeSummary(items: DimensionDraftItem[]): DimensionDraftModuleSummary[] {
  const summary: Record<string, DimensionDraftModuleSummary> = {};
  for (const item of items) {
    const code = item.module || "Other";
    if (!summary[code]) {
      summary[code] = {
        module: code,
        module_label: item.module_label || code,
        needed: false,
        in_scope_count: 0,
        needs_review_count: 0,
      };
    }
    if (item.in_scope) {
      summary[code].needed = true;
      summary[code].in_scope_count += 1;
    }
    if (inferReviewTier(item) === "needs_review") {
      summary[code].needs_review_count = (summary[code].needs_review_count || 0) + 1;
    }
  }
  return Object.values(summary);
}

export default function DimensionBaselineReview({
  draft,
  saving,
  confirming,
  onDraftChange,
  onSaveDraft,
  onConfirm,
}: DimensionBaselineReviewProps) {
  const [customName, setCustomName] = useState("");
  const [customContent, setCustomContent] = useState("");
  const [expandedModules, setExpandedModules] = useState<Set<string>>(new Set());
  const [moduleReviewed, setModuleReviewed] = useState<Set<string>>(new Set());
  const [itemAcknowledged, setItemAcknowledged] = useState<Set<string>>(new Set());
  const [evidenceItem, setEvidenceItem] = useState<DimensionDraftItem | null>(null);

  const items = draft.items || [];
  const reviewSummary = draft.review_summary || computeReviewSummary(items);
  const pendingReview = useMemo(() => needsReviewItems(items), [items]);
  const inScopeModules = useMemo(
    () => modulesWithInScope([...items, ...(draft.custom_items || [])]),
    [items, draft.custom_items],
  );
  const allItems = useMemo(
    () => [...items, ...(draft.custom_items || [])],
    [items, draft.custom_items],
  );
  const inScopeCount = allItems.filter((i) => i.in_scope).length;

  const grouped = useMemo(() => {
    const map = new Map<string, DimensionDraftItem[]>();
    for (const item of items) {
      const key = item.module || "Other";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(item);
    }
    return map;
  }, [items]);

  const visibleModules = useMemo(() => {
    return [...grouped.entries()]
      .map(([code, moduleItems]) => ({
        code,
        label: moduleItems[0]?.module_label || code,
        moduleItems,
      }))
      .filter(({ moduleItems }) => moduleMatchesFilter(moduleItems, "review"));
  }, [grouped]);

  const reviewModuleCount = useMemo(
    () => countModulesForFilter(grouped, "review"),
    [grouped],
  );

  const visibleRowCount = useMemo(
    () =>
      visibleModules.reduce((sum, { moduleItems }) => sum + moduleItems.length, 0),
    [visibleModules],
  );

  const unackedPending = useMemo(
    () => pendingReview.filter((i) => !itemAcknowledged.has(i.dimension_id)),
    [pendingReview, itemAcknowledged],
  );

  const markAcknowledged = (dimensionId: string) => {
    setItemAcknowledged((prev) => new Set(prev).add(dimensionId));
  };

  const clearAcknowledged = (dimensionId: string) => {
    setItemAcknowledged((prev) => {
      if (!prev.has(dimensionId)) return prev;
      const next = new Set(prev);
      next.delete(dimensionId);
      return next;
    });
  };

  const clearModuleAcknowledged = (moduleCode: string) => {
    setItemAcknowledged((prev) => {
      const next = new Set(prev);
      let changed = false;
      for (const item of items) {
        if (item.module === moduleCode && next.delete(item.dimension_id)) {
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  };

  const markModuleReviewed = (moduleCode: string) => {
    setModuleReviewed((prev) => new Set(prev).add(moduleCode));
    setExpandedModules((prev) => new Set(prev).add(moduleCode));
  };

  const handleCollapseChange = (keys: string | string[]) => {
    const keyArr = (Array.isArray(keys) ? keys : [keys]).filter(Boolean) as string[];
    setExpandedModules(new Set(keyArr));
    setModuleReviewed((prev) => {
      const next = new Set(prev);
      keyArr.forEach((k) => next.add(k));
      return next;
    });
  };

  const updateItem = (dimensionId: string, patch: Partial<DimensionDraftItem>, custom = false) => {
    if (patch.in_scope === false) {
      clearAcknowledged(dimensionId);
    } else if (patch.in_scope === true) {
      markAcknowledged(dimensionId);
    }
    if (custom) {
      const customItems = (draft.custom_items || []).map((item) =>
        item.dimension_id === dimensionId ? { ...item, ...patch, manually_adjusted: true } : item,
      );
      onDraftChange({
        ...draft,
        custom_items: customItems,
        module_summary: recomputeSummary([...items, ...customItems]),
      });
      return;
    }
    if (patch.work_content !== undefined && patch.in_scope !== false) {
      markAcknowledged(dimensionId);
    }
    const nextItems = items.map((item) => {
      if (item.dimension_id !== dimensionId) return item;
      const next = { ...item, ...patch, manually_adjusted: true };
      if (next.in_scope === false) next.work_content = "—";
      else if (!next.work_content || next.work_content === "—") next.work_content = next.name;
      return next;
    });
    onDraftChange({
      ...draft,
      items: nextItems,
      module_summary: recomputeSummary([...nextItems, ...(draft.custom_items || [])]),
      review_summary: computeReviewSummary(nextItems),
    });
  };

  const setModuleInScope = (moduleCode: string, inScope: boolean) => {
    markModuleReviewed(moduleCode);
    if (!inScope) {
      clearModuleAcknowledged(moduleCode);
    } else {
      setItemAcknowledged((prev) => {
        const next = new Set(prev);
        for (const item of items) {
          if (item.module === moduleCode) next.add(item.dimension_id);
        }
        return next;
      });
    }
    const nextItems = items.map((item) => {
      if (item.module !== moduleCode) return item;
      return {
        ...item,
        in_scope: inScope,
        work_content:
          inScope ? (item.work_content === "—" ? item.name : item.work_content) : "—",
        manually_adjusted: true,
      };
    });
    onDraftChange({
      ...draft,
      items: nextItems,
      module_summary: recomputeSummary([...nextItems, ...(draft.custom_items || [])]),
      review_summary: computeReviewSummary(nextItems),
    });
  };

  const addCustomItem = () => {
    const name = customName.trim();
    if (!name) return;
    const item: DimensionDraftItem = {
      dimension_id: `custom_${Date.now()}`,
      module: "Custom",
      module_label: "自定义",
      name,
      in_scope: true,
      work_content: customContent.trim() || name,
      custom: true,
      manually_adjusted: true,
      review_tier: "needs_review",
      match_type: "none",
      source_label: "—",
    };
    markAcknowledged(item.dimension_id);
    const customItems = [...(draft.custom_items || []), item];
    onDraftChange({
      ...draft,
      custom_items: customItems,
      module_summary: recomputeSummary([...items, ...customItems]),
    });
    setCustomName("");
    setCustomContent("");
  };

  const unreviewedInScopeModules = [...inScopeModules].filter(
    (m) => m !== "Custom" && !moduleReviewed.has(m),
  );
  const confirmBlockedReason = (() => {
    if (inScopeCount === 0) return "至少勾选 1 项维度后方可确认";
    if (unreviewedInScopeModules.length > 0) {
      const label =
        visibleModules.find((m) => m.code === unreviewedInScopeModules[0])?.label ||
        unreviewedInScopeModules[0];
      return `请先展开【${label}】模块过目`;
    }
    if (unackedPending.length > 0) {
      return `还有 ${unackedPending.length} 项待确认未处理`;
    }
    return null;
  })();

  const renderEvidenceCell = (row: DimensionDraftItem) => {
    const display = resolveEvidenceDisplay(row);
    if (display.summaryLine === "—") return <Text type="secondary">—</Text>;
    return (
      <Button
        type="link"
        size="small"
        style={{ padding: 0, height: "auto", textAlign: "left", whiteSpace: "normal" }}
        onClick={() => setEvidenceItem(row)}
      >
        <div>
          <div>{display.summaryLine}</div>
          {display.subLine && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {display.subLine}
            </Text>
          )}
        </div>
      </Button>
    );
  };

  const renderStatusCell = (row: DimensionDraftItem) => {
    const tier = inferReviewTier(row);
    if (!row.in_scope) {
      if (tier === "auto_include") {
        return <Tag color="green">系统推荐</Tag>;
      }
      return <Text type="secondary">未纳入</Text>;
    }
    if (tier === "auto_include") {
      return <Tag color="green">自动纳入</Tag>;
    }
    if (tier === "auto_exclude") {
      return <Tag>已排除</Tag>;
    }
    return <Tag color="blue">已纳入</Tag>;
  };

  const buildReviewTableColumns = (moduleCode: string, moduleItems: DimensionDraftItem[]) => {
    const allInScope = moduleItems.length > 0 && moduleItems.every((i) => i.in_scope);
    const someInScope = moduleItems.some((i) => i.in_scope);
    return [
      {
        title: () => (
          <Checkbox
            indeterminate={someInScope && !allInScope}
            checked={allInScope}
            onChange={(e) => setModuleInScope(moduleCode, e.target.checked)}
          />
        ),
        width: 70,
        render: (_: unknown, row: DimensionDraftItem) => (
          <Checkbox
            checked={row.in_scope}
            onChange={(e) => updateItem(row.dimension_id, { in_scope: e.target.checked })}
          />
        ),
      },
      { title: "维度", dataIndex: "name", width: 160 },
      {
        title: "工作内容",
        dataIndex: "work_content",
        render: (value: string, row: DimensionDraftItem) =>
          row.in_scope ? (
            <Input
              size="small"
              value={value === "—" ? "" : value}
              onChange={(e) => updateItem(row.dimension_id, { work_content: e.target.value })}
            />
          ) : (
            <Text type="secondary">—</Text>
          ),
      },
      {
        title: "RFQ 依据",
        width: 240,
        render: (_: unknown, row: DimensionDraftItem) => renderEvidenceCell(row),
      },
      {
        title: "匹配方式",
        width: 120,
        render: (_: unknown, row: DimensionDraftItem) => {
          const meta = inferMatchMeta(row);
          return <Tag color={matchTypeTagColor(meta.match_type)}>{meta.source_label}</Tag>;
        },
      },
      {
        title: "状态",
        width: 100,
        render: (_: unknown, row: DimensionDraftItem) => renderStatusCell(row),
      },
    ];
  };

  const collapseItems = visibleModules.map(({ code, label, moduleItems }) => {
    const scoped = moduleItems.filter((i) => i.in_scope).length;
    const excluded = moduleItems.filter((i) => inferReviewTier(i) === "auto_exclude").length;
    const statusLabel = formatModuleStatusLabel(moduleItems, itemAcknowledged);
    return {
      key: code,
      label: (
        <Space wrap>
          <Text strong>{label}</Text>
          <Text type="secondary">{statusLabel}</Text>
          <Text type="secondary">
            （{scoped}/{moduleItems.length} 已勾选）
          </Text>
          {excluded > 0 && (
            <Text type="secondary">· {excluded} 项已排除</Text>
          )}
          {moduleReviewed.has(code) && <Tag color="blue">已过目</Tag>}
        </Space>
      ),
      children: (
        <Table
          rowKey="dimension_id"
          size="small"
          pagination={false}
          dataSource={moduleItems}
          columns={buildReviewTableColumns(code, moduleItems)}
        />
      ),
    };
  });

  return (
    <div style={{ paddingBottom: 8 }}>
      <Alert
        type="info"
        showIcon
        message="基准维度确认（F1.10c）"
        description="仅展示与 RFQ 相关的模块；展开后可查看该模块全部维度（含已排除项）。勾选即纳入，取消勾选即排除。"
        style={{ marginBottom: 16 }}
      />

      <div style={STICKY_TOOLBAR_STYLE}>
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Text type="secondary">
            共 {reviewSummary.total} 项 · 已纳入{" "}
            <Text strong>{inScopeCount}</Text>
            {" · "}
            待确认{" "}
            <Text type="danger" strong>
              {unackedPending.length}
            </Text>
            {" · "}
            {reviewModuleCount} 个相关模块 / {visibleRowCount} 行
          </Text>
        </Space>
      </div>

      {collapseItems.length === 0 ? (
        <Alert
          type="info"
          showIcon
          message="当前无与 RFQ 相关的模块"
          style={{ marginBottom: 16 }}
        />
      ) : (
        <Collapse
          activeKey={[...expandedModules]}
          onChange={handleCollapseChange}
          items={collapseItems}
          style={{ marginBottom: 16 }}
        />
      )}

      {(draft.custom_items || []).length > 0 && (
        <Table
          style={{ marginTop: 16 }}
          rowKey="dimension_id"
          size="small"
          pagination={false}
          title={() => "自定义维度"}
          dataSource={draft.custom_items}
          columns={[
            {
              title: "纳入",
              width: 70,
              render: (_: unknown, row: DimensionDraftItem) => (
                <Checkbox
                  checked={row.in_scope}
                  onChange={(e) => updateItem(row.dimension_id, { in_scope: e.target.checked }, true)}
                />
              ),
            },
            { title: "名称", dataIndex: "name" },
            {
              title: "工作内容",
              dataIndex: "work_content",
              render: (value: string, row: DimensionDraftItem) => (
                <Input
                  size="small"
                  value={value}
                  onChange={(e) =>
                    updateItem(row.dimension_id, { work_content: e.target.value }, true)
                  }
                />
              ),
            },
          ]}
        />
      )}

      <Space wrap style={{ marginTop: 16 }}>
        <Input
          placeholder="自定义维度名称"
          value={customName}
          onChange={(e) => setCustomName(e.target.value)}
          style={{ width: 200 }}
        />
        <Input
          placeholder="工作内容（可选）"
          value={customContent}
          onChange={(e) => setCustomContent(e.target.value)}
          style={{ width: 240 }}
        />
        <Button onClick={addCustomItem}>补充自定义维度</Button>
      </Space>

      <div style={STICKY_FOOTER_STYLE}>
        <Space wrap align="start">
          <Button loading={saving} onClick={onSaveDraft}>
            保存勾选
          </Button>
          <Button
            type="primary"
            loading={confirming}
            disabled={!!confirmBlockedReason}
            onClick={onConfirm}
          >
            确认以上例外，生成对比矩阵
          </Button>
          {confirmBlockedReason && <Text type="warning">{confirmBlockedReason}</Text>}
        </Space>
      </div>

      <Drawer
        title={evidenceItem ? `RFQ 依据 — ${evidenceItem.name}` : "RFQ 依据"}
        open={!!evidenceItem}
        onClose={() => setEvidenceItem(null)}
        width={480}
      >
        {evidenceItem && (() => {
          const display = resolveEvidenceDisplay(evidenceItem);
          return (
            <>
              {(display.section || display.chapterTitle) && (
                <Alert
                  type="info"
                  showIcon={false}
                  message={
                    <Space direction="vertical" size={0}>
                      {display.section && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          §{display.section}
                        </Text>
                      )}
                      {display.chapterTitle && (
                        <Text strong style={{ fontSize: 15 }}>
                          {display.chapterTitle}
                        </Text>
                      )}
                    </Space>
                  }
                  style={{ marginBottom: 16 }}
                />
              )}
              <Descriptions column={1} size="small">
                <Descriptions.Item label="匹配方式">
                  {inferMatchMeta(evidenceItem).source_label}
                </Descriptions.Item>
                {display.matchedKeyword && (
                  <Descriptions.Item label="匹配关键词">{display.matchedKeyword}</Descriptions.Item>
                )}
                <Descriptions.Item label="RFQ 出处">{evidenceItem.source_ref || "—"}</Descriptions.Item>
                <Descriptions.Item label="RFQ 摘录">
                  <Text>{display.snippet || "—"}</Text>
                </Descriptions.Item>
              </Descriptions>
            </>
          );
        })()}
      </Drawer>
    </div>
  );
}
