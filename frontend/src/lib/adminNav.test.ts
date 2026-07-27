import { describe, expect, it } from "vitest";
import {
  canAccessAdminOpsNav,
  canAccessUserAdmin,
  summarizeAiHealth,
} from "./adminNav";

describe("admin ops nav gates", () => {
  it("allows ops for kb_admin and auth-off local", () => {
    expect(canAccessAdminOpsNav({ authEnabled: true, isKbAdmin: true })).toBe(true);
    expect(canAccessAdminOpsNav({ authEnabled: false, isKbAdmin: false })).toBe(true);
    expect(canAccessAdminOpsNav({ authEnabled: true, isKbAdmin: false })).toBe(false);
  });

  it("restricts user admin to authenticated kb_admin", () => {
    expect(canAccessUserAdmin({ authEnabled: true, isKbAdmin: true })).toBe(true);
    expect(canAccessUserAdmin({ authEnabled: false, isKbAdmin: true })).toBe(false);
    expect(canAccessUserAdmin({ authEnabled: true, isKbAdmin: false })).toBe(false);
  });
});

describe("summarizeAiHealth", () => {
  it("reports ok when ollama and models are ready", () => {
    const s = summarizeAiHealth({
      status: "ok",
      version: "1",
      model: "qwen",
      embedding_model: "nomic",
      mock_llm: false,
      mock_rag: false,
      ollama_reachable: true,
      ollama_model_ready: true,
      embedding_model_ready: true,
    });
    expect(s.tone).toBe("ok");
    expect(s.label).toMatch(/可用/);
  });

  it("reports error when ollama unreachable", () => {
    const s = summarizeAiHealth({
      status: "degraded",
      version: "1",
      model: "qwen",
      embedding_model: "nomic",
      mock_llm: false,
      mock_rag: false,
      ollama_reachable: false,
      ollama_model_ready: false,
      embedding_model_ready: false,
      ollama_error: "connection refused",
    });
    expect(s.tone).toBe("error");
    expect(s.detail).toMatch(/connection refused/);
  });
});
