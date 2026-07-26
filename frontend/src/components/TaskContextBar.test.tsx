import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import TaskContextBar from "@/components/TaskContextBar";
import type { TaskPayload } from "@/types/task";

const pathnameRef = { current: "/quote" };
const taskRef = { current: null as TaskPayload | null };

vi.mock("next/navigation", () => ({
  usePathname: () => pathnameRef.current,
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: unknown }) => (
    <a href={href}>{children as never}</a>
  ),
}));

vi.mock("@/context/TaskContext", () => ({
  useTaskContext: () => ({
    task: taskRef.current,
    loading: false,
  }),
}));

vi.mock("@/components/WorkflowSteps", () => ({
  default: () => <div data-testid="workflow-steps" />,
}));

const getMock = vi.fn();
vi.mock("@/api/client", () => ({
  apiClient: {
    get: (...args: unknown[]) => getMock(...args),
  },
}));

function queuedTask(overrides?: Partial<TaskPayload>): TaskPayload {
  return {
    task_id: "task-queued-1",
    file_name: "RFQ_客户A.doc",
    processing_status: "queued",
    status: "draft",
    status_message: "排队等待处理",
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  pathnameRef.current = "/quote";
  taskRef.current = null;
});

beforeEach(() => {
  getMock.mockResolvedValue({
    data: {
      status: "queued",
      queue_position: 2,
      estimated_wait_seconds: 240,
    },
  });
});

describe("TaskContextBar PERF11", () => {
  it("hides on /rfq and does not poll status", async () => {
    pathnameRef.current = "/rfq";
    taskRef.current = queuedTask();
    const { container } = render(<TaskContextBar />);
    expect(container).toBeEmptyDOMElement();
    await waitFor(() => {
      expect(getMock).not.toHaveBeenCalled();
    });
  });

  it("hides on /knowledge", () => {
    pathnameRef.current = "/knowledge";
    taskRef.current = queuedTask();
    const { container } = render(<TaskContextBar />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows queue headline, tag, hint and open link on /quote", async () => {
    pathnameRef.current = "/quote";
    taskRef.current = queuedTask();
    render(<TaskContextBar />);

    expect(screen.getByTestId("task-context-bar")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("task-context-bar-headline")).toHaveTextContent(
        "RFQ_客户A.doc 正在排队（第 2 位）",
      );
    });
    expect(screen.getByTestId("task-context-bar-tag")).toHaveTextContent("排队中");
    expect(screen.getByTestId("task-context-bar-queue")).toHaveTextContent("第 2 位");
    expect(screen.getByRole("link", { name: "查看进度" })).toHaveAttribute(
      "href",
      "/rfq?task_id=task-queued-1",
    );
    expect(getMock).toHaveBeenCalledWith(
      "/rfq/tasks/task-queued-1/status",
      expect.objectContaining({ silentError: true }),
    );
  });

  it("shows 待您确认 and confirm CTA for dimension_review without polling", async () => {
    pathnameRef.current = "/qa";
    taskRef.current = queuedTask({
      processing_status: "dimension_review",
      status_message: "等待工程师确认",
    });
    render(<TaskContextBar />);

    expect(screen.getByTestId("task-context-bar-headline")).toHaveTextContent(
      "待您确认基准维度",
    );
    expect(screen.getByTestId("task-context-bar-tag")).toHaveTextContent("待您确认");
    expect(screen.getByRole("link", { name: "前往确认维度" })).toHaveAttribute(
      "href",
      "/rfq?task_id=task-queued-1",
    );
    expect(screen.queryByTestId("task-context-bar-queue")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(getMock).not.toHaveBeenCalled();
    });
  });

  it("shows empty-state when no task loaded", () => {
    pathnameRef.current = "/proposal";
    taskRef.current = null;
    render(<TaskContextBar />);
    expect(screen.getByText(/尚未加载任务/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "前往 RFQ 分析上传或选择任务" })).toHaveAttribute(
      "href",
      "/rfq",
    );
  });
});
