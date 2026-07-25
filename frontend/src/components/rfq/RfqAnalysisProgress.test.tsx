import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Modal } from "antd";
import { afterEach, describe, expect, it, vi } from "vitest";
import RfqAnalysisProgress from "@/components/rfq/RfqAnalysisProgress";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("RfqAnalysisProgress cancel controls", () => {
  it("shows cancel button for queued analysis and confirms before calling onCancel", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    const confirmSpy = vi.spyOn(Modal, "confirm").mockImplementation((config) => {
      config.onOk?.();
      return { destroy: vi.fn(), update: vi.fn() } as ReturnType<typeof Modal.confirm>;
    });

    render(
      <RfqAnalysisProgress
        progress={0}
        message="排队等待处理"
        processingStatus="queued"
        queuePosition={1}
        estimatedWaitSeconds={120}
        onCancel={onCancel}
      />,
    );

    expect(screen.getByRole("heading", { name: "排队等待处理" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("排队中：第 1 位");
    expect(screen.getByRole("status")).toHaveTextContent("预计还需约 2 分钟");

    const cancelBtn = screen.getByTestId("rfq-cancel-analysis");
    expect(cancelBtn).toBeEnabled();
    expect(cancelBtn).toHaveTextContent("取消分析");
    await user.click(cancelBtn);

    expect(confirmSpy).toHaveBeenCalled();
    const confirmArg = confirmSpy.mock.calls[0]?.[0] as {
      title?: string;
      content?: string;
      okText?: string;
    };
    expect(confirmArg.title).toBe("取消分析");
    expect(String(confirmArg.content)).toContain("将停止当前分析");
    expect(confirmArg.okText).toBe("确定取消");
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("shows cancelling button and phase1 hint without marking engineer review done", () => {
    render(
      <RfqAnalysisProgress
        progress={40}
        message="正在取消分析，当前模型调用结束后停止"
        processingStatus="cancelling"
        cancelling
        onCancel={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("heading", {
        name: "正在取消分析，当前模型调用结束后停止",
      }),
    ).toBeInTheDocument();

    const cancelBtn = screen.getByTestId("rfq-cancel-analysis");
    expect(cancelBtn).toBeDisabled();
    expect(cancelBtn).toHaveTextContent("正在取消…");
    expect(
      screen.getByText("正在等待当前模型输出结束，结束后立即释放队列"),
    ).toBeInTheDocument();
    expect(screen.getByText("正在取消")).toBeInTheDocument();
    expect(screen.getByText("等待工程师确认")).toBeInTheDocument();
    const review = screen.getByText("等待工程师确认");
    const cancelStep = screen.getByText("正在取消");
    expect(
      review.compareDocumentPosition(cancelStep) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("keeps cancel control visible while optimistic cancelling on queued task", () => {
    render(
      <RfqAnalysisProgress
        progress={0}
        message="排队等待处理"
        processingStatus="queued"
        queuePosition={2}
        cancelling
        onCancel={vi.fn()}
      />,
    );

    const cancelBtn = screen.getByTestId("rfq-cancel-analysis");
    expect(cancelBtn).toBeDisabled();
    expect(cancelBtn).toHaveTextContent("正在取消…");
    expect(
      screen.getByText("正在等待当前模型输出结束，结束后立即释放队列"),
    ).toBeInTheDocument();
  });

  it("does not show cancel button when onCancel is omitted", () => {
    render(
      <RfqAnalysisProgress
        progress={20}
        message="正在解析 RFQ 文档..."
        processingStatus="parsing"
      />,
    );

    expect(screen.queryByTestId("rfq-cancel-analysis")).not.toBeInTheDocument();
  });

  it("shows resume control when stalled", async () => {
    const user = userEvent.setup();
    const onResume = vi.fn();
    render(
      <RfqAnalysisProgress
        progress={20}
        message="正在解析 RFQ 文档..."
        processingStatus="parsing"
        stalled
        onResumePolling={onResume}
      />,
    );

    const resume = screen.getByRole("button", { name: "继续等待" });
    await user.click(resume);
    expect(onResume).toHaveBeenCalledTimes(1);
  });

  it("shows live timing and queue checklist for waiting task", () => {
    const { container } = render(
      <RfqAnalysisProgress
        progress={0}
        message="排队等待处理"
        processingStatus="queued"
        queuePosition={1}
        estimatedWaitSeconds={90}
        queueWaitMs={164000}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByTestId("rfq-live-timing")).toHaveTextContent("已等待");
    const checklist = container.querySelectorAll("div");
    const labels = Array.from(container.querySelectorAll("span")).map((el) => el.textContent);
    expect(labels).toContain("文件上传");
    expect(labels).toContain("排队等待");
    expect(labels).toContain("解析 RFQ 文档");
    expect(screen.getByTestId("rfq-cancel-analysis")).toBeInTheDocument();
    expect(checklist.length).toBeGreaterThan(0);
    expect(within(screen.getByRole("status")).getByText(/预计还需约/)).toBeInTheDocument();
  });
});
