import { describe, expect, it } from "vitest";
import { capacityAlert, formatCapacityBytes } from "./kbCapacity";

describe("knowledge base capacity state", () => {
  it("hides healthy volume state", () => {
    expect(
      capacityAlert({
        volume: "data",
        total_bytes: 100,
        used_bytes: 50,
        free_bytes: 50,
        usage_percent: 50,
        warning: false,
        write_protected: false,
      }),
    ).toBeNull();
  });

  it("explains write protection without implying reads are down", () => {
    const alert = capacityAlert({
      volume: "data",
      total_bytes: 100 * 1024 ** 3,
      used_bytes: 95 * 1024 ** 3,
      free_bytes: 5 * 1024 ** 3,
      usage_percent: 95,
      warning: true,
      write_protected: true,
    });

    expect(alert?.type).toBe("error");
    expect(alert?.description).toContain("上传和索引已暂停");
    expect(alert?.description).toContain("检索与下载仍可使用");
  });

  it("formats capacity using readable binary units", () => {
    expect(formatCapacityBytes(5 * 1024 ** 3)).toBe("5.0 GB");
  });
});
