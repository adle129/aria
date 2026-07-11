"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { apiClient, clearStoredTaskId, LAST_TASK_ID_KEY } from "@/api/client";
import type { TaskPayload, TaskSummary } from "@/types/task";

export const TASK_CHANGED_EVENT = "aria-task-changed";

export function notifyTaskChanged(taskId: string) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(LAST_TASK_ID_KEY, taskId);
  window.dispatchEvent(new CustomEvent(TASK_CHANGED_EVENT, { detail: taskId }));
}

interface TaskContextValue {
  taskId: string;
  task: TaskPayload | null;
  loading: boolean;
  recentTasks: TaskSummary[];
  setTaskId: (id: string) => void;
  loadTask: (id?: string) => Promise<TaskPayload | null>;
  refreshRecentTasks: () => Promise<void>;
  syncFromPayload: (payload: TaskPayload) => void;
  clearTask: () => void;
}

const TaskContext = createContext<TaskContextValue | null>(null);

function isNotFoundError(err: unknown): boolean {
  return (err as { response?: { status?: number } })?.response?.status === 404;
}

export function TaskProvider({ children }: { children: ReactNode }) {
  const [taskId, setTaskIdState] = useState("");
  const [task, setTask] = useState<TaskPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [recentTasks, setRecentTasks] = useState<TaskSummary[]>([]);

  const clearTask = useCallback(() => {
    clearStoredTaskId();
    setTaskIdState("");
    setTask(null);
  }, []);

  const refreshRecentTasks = useCallback(async () => {
    try {
      const resp = await apiClient.get<{ code: number; data: TaskSummary[] }>("/rfq/tasks", {
        // Keep every upload visible — same file_name can have multiple tasks.
        params: { limit: 50, unique_file: false },
      });
      const rows = resp.data.data || [];
      setRecentTasks(rows);
    } catch {
      // optional UX
    }
  }, []);

  const loadTask = useCallback(async (rawId?: string) => {
    const id = (rawId ?? taskId).trim();
    if (!id) return null;
    setTaskIdState(id);
    setLoading(true);
    try {
      const resp = await apiClient.get<{ code: number; data: TaskPayload }>(`/rfq/tasks/${id}`, {
        showError: true,
      });
      const payload = resp.data.data;
      setTask(payload);
      notifyTaskChanged(id);
      return payload;
    } catch (err) {
      if (isNotFoundError(err)) {
        clearTask();
      } else {
        setTask(null);
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, [clearTask, taskId]);

  const syncFromPayload = useCallback((payload: TaskPayload) => {
    setTask(payload);
    setTaskIdState(payload.task_id);
    notifyTaskChanged(payload.task_id);
  }, []);

  const setTaskId = useCallback((id: string) => {
    setTaskIdState(id);
  }, []);

  useEffect(() => {
    void refreshRecentTasks();
  }, [refreshRecentTasks]);

  useEffect(() => {
    const stored =
      typeof window !== "undefined" ? sessionStorage.getItem(LAST_TASK_ID_KEY)?.trim() : "";
    if (stored) {
      setTaskIdState(stored);
      void (async () => {
        setLoading(true);
        try {
          const resp = await apiClient.get<{ code: number; data: TaskPayload }>(
            `/rfq/tasks/${stored}`,
            { silentError: true },
          );
          setTask(resp.data.data);
        } catch (err) {
          if (isNotFoundError(err)) {
            clearTask();
          } else {
            setTask(null);
          }
        } finally {
          setLoading(false);
        }
      })();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount restore only
  }, []);

  useEffect(() => {
    const onChanged = (event: Event) => {
      const id = (event as CustomEvent<string>).detail?.trim();
      if (id && id !== taskId) {
        setTaskIdState(id);
        void loadTask(id);
      }
    };
    window.addEventListener(TASK_CHANGED_EVENT, onChanged);
    return () => window.removeEventListener(TASK_CHANGED_EVENT, onChanged);
  }, [loadTask, taskId]);

  const value = useMemo(
    () => ({
      taskId,
      task,
      loading,
      recentTasks,
      setTaskId,
      loadTask,
      refreshRecentTasks,
      syncFromPayload,
      clearTask,
    }),
    [taskId, task, loading, recentTasks, setTaskId, loadTask, refreshRecentTasks, syncFromPayload, clearTask],
  );

  return <TaskContext.Provider value={value}>{children}</TaskContext.Provider>;
}

export function useTaskContext(): TaskContextValue {
  const ctx = useContext(TaskContext);
  if (!ctx) {
    throw new Error("useTaskContext must be used within TaskProvider");
  }
  return ctx;
}
