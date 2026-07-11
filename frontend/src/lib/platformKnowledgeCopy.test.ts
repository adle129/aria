import { describe, expect, it } from "vitest";
import {
  ENGINEER_FORBIDDEN_TERMS,
  engineerExplainerPlainText,
} from "./platformKnowledgeCopy";

describe("engineer knowledge explainer copy", () => {
  it("avoids infra and delivery jargon for formal and demo", () => {
    for (const demo of [false, true]) {
      const text = engineerExplainerPlainText(demo);
      for (const term of ENGINEER_FORBIDDEN_TERMS) {
        expect(text).not.toContain(term);
      }
      expect(text).toMatch(/RFQ 分析/);
      expect(text).toMatch(/资料库管理员/);
    }
  });
});
