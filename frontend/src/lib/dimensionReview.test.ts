import { describe, expect, it } from "vitest";
import type { DimensionDraftItem } from "@/types/task";
import {
  computeReviewSummary,
  formatEvidenceLine,
  formatModuleStatusLabel,
  inferReviewTier,
  moduleReviewTableItems,
  needsReviewItems,
  resolveEvidenceDisplay,
} from "./dimensionReview";

function item(partial: Partial<DimensionDraftItem> & Pick<DimensionDraftItem, "dimension_id" | "name">): DimensionDraftItem {
  return {
    in_scope: false,
    ...partial,
  };
}

describe("resolveEvidenceDisplay", () => {
  it("prefers section title over keyword-only summary", () => {
    const display = resolveEvidenceDisplay(
      item({
        dimension_id: "biw_body_structure",
        name: "白车身结构",
        match_type: "keywords",
        source_ref: "RFQ §4.1.2 · 车身系统开发",
        evidence: {
          rfq_section: "4.1.2",
          rfq_section_title: "车身系统开发",
          matched_keyword: "BIW",
          snippet: "白车身 BIW 结构设计与验证",
        },
      }),
    );
    expect(display.summaryLine).toBe("§4.1.2 车身系统开发");
    expect(display.subLine).toBe("关键词「BIW」");
    expect(display.snippet).not.toMatch(/\{'id'/);
  });

  it("uses customer keyword phrasing when section is missing", () => {
    const display = resolveEvidenceDisplay(
      item({
        dimension_id: "x",
        name: "测试",
        evidence: { matched_keyword: "BIW" },
      }),
    );
    expect(display.summaryLine).toBe("关键词「BIW」");
    expect(display.summaryLine).not.toContain("命中");
  });

  it("parses section from source_ref when evidence lacks rfq_section", () => {
    const display = resolveEvidenceDisplay(
      item({
        dimension_id: "x",
        name: "测试",
        source_ref: "RFQ §4.1.2 · 车身系统开发",
        evidence: { matched_keyword: "BIW", snippet: "白车身 BIW 结构设计与验证" },
      }),
    );
    expect(display.section).toBe("4.1.2");
    expect(display.chapterTitle).toBe("车身系统开发");
  });
});

describe("formatEvidenceLine", () => {
  it("does not surface structured dump snippets", () => {
    const line = formatEvidenceLine(
      item({
        dimension_id: "bad",
        name: "坏数据",
        evidence: {
          matched_keyword: "BIW",
          snippet: "[{'id': '4.1.2', 'title': '车身系统开发', 'function': 'BIW'}]",
        },
      }),
    );
    expect(line).toBe("关键词「BIW」");
    expect(line).not.toContain("{");
  });
});

describe("moduleReviewTableItems", () => {
  const moduleItems: DimensionDraftItem[] = [
    item({
      dimension_id: "a",
      name: "已纳入",
      module: "BIW",
      in_scope: true,
      review_tier: "auto_include",
    }),
    item({
      dimension_id: "b",
      name: "待确认",
      module: "BIW",
      in_scope: true,
      review_tier: "needs_review",
    }),
    item({
      dimension_id: "c",
      name: "系统推荐未勾选",
      module: "BIW",
      in_scope: false,
      review_tier: "auto_include",
    }),
    item({
      dimension_id: "d",
      name: "已排除",
      module: "BIW",
      in_scope: false,
      review_tier: "auto_exclude",
    }),
  ];

  it("includes auto_include rows even when unchecked", () => {
    const visible = moduleReviewTableItems(moduleItems);
    expect(visible.map((i) => i.dimension_id)).toEqual(["a", "b", "c"]);
  });

  it("aligns visible count with formatModuleStatusLabel buckets", () => {
    const visible = moduleReviewTableItems(moduleItems);
    const label = formatModuleStatusLabel(moduleItems);
    expect(label).toContain("已纳入 2 项");
    expect(label).toContain("1 项系统推荐纳入");
    expect(label).toContain("1 项待确认");
    expect(visible.filter((i) => i.in_scope).length).toBe(2);
  });
});

describe("computeReviewSummary", () => {
  it("counts tiers consistently with inferReviewTier", () => {
    const items: DimensionDraftItem[] = [
      item({ dimension_id: "1", name: "a", review_tier: "auto_include", in_scope: true }),
      item({ dimension_id: "2", name: "b", review_tier: "needs_review", in_scope: true }),
      item({ dimension_id: "3", name: "c", review_tier: "auto_exclude", in_scope: false }),
    ];
    const summary = computeReviewSummary(items);
    expect(summary.total).toBe(3);
    expect(summary.auto_include).toBe(1);
    expect(summary.needs_review).toBe(1);
    expect(summary.auto_exclude).toBe(1);
  });
});

describe("needsReviewItems", () => {
  it("only returns in_scope needs_review rows for pending confirm count", () => {
    const items: DimensionDraftItem[] = [
      item({ dimension_id: "1", name: "a", review_tier: "needs_review", in_scope: true }),
      item({ dimension_id: "2", name: "b", review_tier: "needs_review", in_scope: false }),
    ];
    expect(needsReviewItems(items).map((i) => i.dimension_id)).toEqual(["1"]);
    expect(inferReviewTier(items[1]!)).toBe("needs_review");
  });
});
