/** @vitest-environment happy-dom */
import { afterEach, describe, expect, it, vi } from "vitest";
import { LAST_TASK_ID_KEY } from "@/api/client";
import {
  notifyTaskChanged,
  rememberLastTaskId,
  TASK_CHANGED_EVENT,
} from "@/lib/taskSelection";

describe("taskSelection", () => {
  afterEach(() => {
    sessionStorage.clear();
  });

  it("rememberLastTaskId writes sessionStorage without dispatch", () => {
    const spy = vi.fn();
    window.addEventListener(TASK_CHANGED_EVENT, spy);
    rememberLastTaskId("task-a");
    expect(sessionStorage.getItem(LAST_TASK_ID_KEY)).toBe("task-a");
    expect(spy).not.toHaveBeenCalled();
    window.removeEventListener(TASK_CHANGED_EVENT, spy);
  });

  it("notifyTaskChanged persists and dispatches once", () => {
    const spy = vi.fn();
    window.addEventListener(TASK_CHANGED_EVENT, spy);
    notifyTaskChanged("task-b");
    expect(sessionStorage.getItem(LAST_TASK_ID_KEY)).toBe("task-b");
    expect(spy).toHaveBeenCalledTimes(1);
    expect((spy.mock.calls[0][0] as CustomEvent<string>).detail).toBe("task-b");
    window.removeEventListener(TASK_CHANGED_EVENT, spy);
  });
});
