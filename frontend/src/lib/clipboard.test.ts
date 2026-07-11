import { afterEach, describe, expect, it, vi } from "vitest";
import { copyToClipboard, formatTaskShortId } from "./clipboard";

describe("formatTaskShortId", () => {
  it("returns first 8 characters", () => {
    expect(formatTaskShortId("8592c17d-abcd-ef01-2345-6789abcdef01")).toBe("8592c17d");
  });
});

describe("copyToClipboard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses navigator.clipboard when available", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    await copyToClipboard("task-123");
    expect(writeText).toHaveBeenCalledWith("task-123");
  });

  it("falls back to execCommand when clipboard API fails", async () => {
    const writeText = vi.fn().mockRejectedValue(new Error("denied"));
    const execCommand = vi.fn().mockReturnValue(true);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    vi.stubGlobal("document", {
      createElement: () => ({
        value: "",
        style: {},
        select: vi.fn(),
      }),
      body: {
        appendChild: vi.fn(),
        removeChild: vi.fn(),
      },
      execCommand,
    });
    await copyToClipboard("task-456");
    expect(execCommand).toHaveBeenCalledWith("copy");
  });
});
