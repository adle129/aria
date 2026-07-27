import { describe, expect, it } from "vitest";
import {
  applyEngagementToInScope,
  buildFunctionSourceSummaryRows,
  coalesceFunctionSourceMap,
  collectSourceCandidates,
  countMappedInScope,
  defaultFunctionSourceMap,
  isColumnFullySelected,
  resolveInScopeFunctions,
  toggleColumnForInScope,
} from "./functionSourceMap";

describe("functionSourceMap", () => {
  it("resolves in-scope sheets in display order", () => {
    expect(
      resolveInScopeFunctions({ functions_in_scope: ["Chassis", "pm"] }),
    ).toEqual(["PM", "Chassis"]);
  });

  it("prefills only in-scope modules", () => {
    const map = defaultFunctionSourceMap(["PM", "BIW"], "eng-a");
    expect(map.PM).toBe("eng-a");
    expect(map.BIW).toBe("eng-a");
    expect(map.Chassis).toBeNull();
  });

  it("keeps matrix project columns even without engagement_id", () => {
    const candidates = collectSourceCandidates(
      [
        { project_name: "Hist A", similarity_score: 0.91, customer: "OEM-A" },
        { project_name: "Hist B", similarity_score: 0.8 },
      ],
      [{ metadata: { engagement_id: "e1", project_name: "Hist A", customer: "OEM-A" } }],
    );
    expect(candidates).toHaveLength(2);
    expect(candidates[0]).toMatchObject({
      engagementId: "e1",
      projectName: "Hist A",
      customer: "OEM-A",
      similarityScore: 0.91,
    });
    expect(candidates[1]).toMatchObject({
      engagementId: null,
      projectName: "Hist B",
      similarityScore: 0.8,
    });
    expect(candidates[1].columnKey).toContain("Hist B");
  });

  it("limits to top 3 candidates", () => {
    const projects = [1, 2, 3, 4].map((n) => ({
      project_name: `P${n}`,
      engagement_id: `e${n}`,
      similarity_score: 1 - n * 0.1,
    }));
    expect(collectSourceCandidates(projects).map((c) => c.engagementId)).toEqual([
      "e1",
      "e2",
      "e3",
    ]);
  });

  it("applies one engagement to all in-scope and counts mapped", () => {
    const base = defaultFunctionSourceMap(["PM", "Chassis"], "e1");
    const cleared = applyEngagementToInScope(base, ["PM", "Chassis"], null);
    expect(cleared.PM).toBeNull();
    expect(countMappedInScope(cleared, ["PM", "Chassis"])).toEqual({
      mapped: 0,
      total: 2,
    });

    const saved = coalesceFunctionSourceMap(
      { PM: "e1", Chassis: null },
      ["PM", "Chassis"],
      "e2",
    );
    expect(saved.PM).toBe("e1");
    expect(saved.Chassis).toBeNull();
  });

  it("toggles column select / clear for in-scope modules", () => {
    const scope = ["PM", "Chassis"] as const;
    const selected = toggleColumnForInScope(
      defaultFunctionSourceMap([...scope], null),
      [...scope],
      "e1",
    );
    expect(isColumnFullySelected(selected, [...scope], "e1")).toBe(true);
    const cleared = toggleColumnForInScope(selected, [...scope], "e1");
    expect(cleared.PM).toBeNull();
    expect(cleared.Chassis).toBeNull();
    expect(isColumnFullySelected(cleared, [...scope], "e1")).toBe(false);
  });

  it("builds read-only summary rows for quote page", () => {
    const candidates = collectSourceCandidates([
      { project_name: "Hist A", engagement_id: "e1" },
      { project_name: "Hist B", engagement_id: "e2" },
    ]);
    const rows = buildFunctionSourceSummaryRows(
      { PM: "e1", Chassis: "e2", BIW: null },
      ["PM", "Chassis"],
      candidates,
    );
    const byKey = Object.fromEntries(rows.map((r) => [r.key, r]));
    expect(byKey.PM).toMatchObject({
      inScope: true,
      sourceLabel: "Hist A",
      engagementId: "e1",
    });
    expect(byKey.Chassis).toMatchObject({
      inScope: true,
      sourceLabel: "Hist B",
      engagementId: "e2",
    });
    expect(byKey.BIW).toMatchObject({
      inScope: false,
      sourceLabel: "不在范围",
      engagementId: null,
    });
  });
});
