import { describe, expect, it } from "vitest";
import {
  computeModuleQualityStats,
  countDeliverableItems,
  groupModulesByFunction,
  isClauseWorkSectionKind,
  isUnassessedComplexity,
  normalizeDeliverableGroups,
  resolveWorkSections,
  sectionUsesWorkItemColumns,
  workSectionCategoryLabel,
} from "./rfqModuleGroups";

describe("rfqModuleGroups", () => {
  it("flags low deliverable coverage and unknown functions", () => {
    const stats = computeModuleQualityStats([
      { function: "GI", deliverables: ["a"], estimated_complexity: "未评估" },
      { function: "未知", deliverables: [], estimated_complexity: "未评估" },
      { function: "BIW", deliverables: [], estimated_complexity: "中" },
      { function: "未知", deliverables: [], estimated_complexity: "未评估" },
    ]);
    expect(stats.total).toBe(4);
    expect(stats.unknownFunction).toBe(2);
    expect(stats.withDeliverables).toBe(1);
    expect(stats.lowDeliverableCoverage).toBe(true);
    expect(stats.manyUnknownFunctions).toBe(true);
    expect(stats.unassessedComplexity).toBe(3);
  });

  it("groups unknown under 待确认 last", () => {
    const groups = groupModulesByFunction([
      { function: "未知", module_name: "x" },
      { function: "GI", module_name: "y" },
      { function: "BIW", module_name: "z" },
    ]);
    expect(groups.map((g) => g.functionKey)).toEqual(["BIW", "GI", "待确认"]);
    expect(groups.map((g) => g.label)).toEqual([
      "车身 (BIW)",
      "总布置 (GI)",
      "待确认（领域未识别）",
    ]);
  });

  it("treats 未评估 as unassessed complexity", () => {
    expect(isUnassessedComplexity("未评估")).toBe(true);
    expect(isUnassessedComplexity("高")).toBe(false);
  });

  it("treats tech/quality as clause sections without domain columns", () => {
    expect(isClauseWorkSectionKind("tech_requirements")).toBe(true);
    expect(isClauseWorkSectionKind("quality")).toBe(true);
    expect(isClauseWorkSectionKind("work_content")).toBe(false);
    expect(sectionUsesWorkItemColumns("tech_requirements", true)).toBe(false);
    expect(sectionUsesWorkItemColumns("quality", true)).toBe(false);
    expect(sectionUsesWorkItemColumns("work_content", false)).toBe(true);
    expect(sectionUsesWorkItemColumns("other", true)).toBe(true);
  });

  it("normalizes deliverable groups by category", () => {
    const groups = normalizeDeliverableGroups([
      { category: "整车总布置交付物", function: "GI", items: ["总体布置分析报告", ""] },
      { category: "", items: [] },
    ]);
    expect(groups).toEqual([
      { category: "整车总布置交付物", function: "GI", items: ["总体布置分析报告"] },
    ]);
    expect(countDeliverableItems(groups)).toBe(1);
  });

  it("preserves stage-tagged deliverable titles", () => {
    const groups = normalizeDeliverableGroups([
      {
        category: "尺寸工程交付物",
        function: "GI",
        items: ["阶段总结报告（P2）", "阶段总结报告（P3）", "项目总结报告（P4）"],
      },
    ]);
    expect(groups[0].items).toEqual([
      "阶段总结报告（P2）",
      "阶段总结报告（P3）",
      "项目总结报告（P4）",
    ]);
    expect(countDeliverableItems(groups)).toBe(3);
  });

  it("uses dynamic L3 label from work_sections", () => {
    const sections = resolveWorkSections(
      [
        {
          title: "工作内容",
          kind: "work_content",
          categories: [
            {
              key: "车身系统开发",
              label: "车身系统开发",
              function: "BIW",
              rows: [{ function: "BIW", module_name: "白车身结构设计" }],
            },
          ],
        },
        {
          title: "技术要求",
          kind: "tech_requirements",
          categories: [
            {
              key: "_all",
              label: "",
              rows: [{ module_name: "准确性要求" }],
            },
          ],
        },
      ],
      [],
    );
    expect(sections.map((s) => s.title)).toEqual(["工作内容", "技术要求"]);
    expect(workSectionCategoryLabel(sections[0].categories[0])).toBe("车身系统开发");
  });

  it("sorts rows so the same function stays contiguous", () => {
    const sections = resolveWorkSections(
      [
        {
          title: "工作内容",
          kind: "work_content",
          categories: [
            {
              key: "尺寸工程开发",
              label: "尺寸工程开发",
              rows: [
                { function: "Interior", module_name: "a", section_id: "4.1.7.1" },
                { function: "BIW", module_name: "b", section_id: "4.1.7.10" },
                { function: "Interior", module_name: "c", section_id: "4.1.7.2" },
                { function: "GI", module_name: "d", section_id: "4.1.7.11" },
              ],
            },
          ],
        },
      ],
      [],
    );
    expect(sections[0].categories[0].rows.map((r) => r.function)).toEqual([
      "BIW",
      "GI",
      "Interior",
      "Interior",
    ]);
  });
});
