"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { apiClient, clearStoredTaskId, LAST_TASK_ID_KEY } from "@/api/client";
import {
  notifyTaskChanged,
  rememberLastTaskId,
  TASK_CHANGED_EVENT,
} from "@/lib/taskSelection";
import type { TaskPayload, TaskSummary } from "@/types/task";

export { TASK_CHANGED_EVENT, notifyTaskChanged, rememberLastTaskId };

interface TaskContextValue {
  taskId: string;
  task: TaskPayload | null;
  loading: boolean;
  recentTasks: TaskSummary[];
  setTaskId: (id: string) => void;
  loadTask: (id?: string) => Promise<TaskPayload | null>;
  refreshRecentTasks: (options?: { force?: boolean }) => Promise<void>;
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
  const taskIdRef = useRef(taskId);
  taskIdRef.current = taskId;
  const lastListRefreshAtRef = useRef(0);
  const listRefreshInFlightRef = useRef<Promise<void> | null>(null);

  const clearTask = useCallback(() => {
    clearStoredTaskId();
    setTaskIdState("");
    setTask(null);
  }, []);

  const refreshRecentTasks = useCallback(async (options?: { force?: boolean }) => {
    const now = Date.now();
    // Poll loops used to call this on every progress tick → request storms + Network Error toasts.
    if (!options?.force && now - lastListRefreshAtRef.current < 2000) {
      return;
    }
    if (listRefreshInFlightRef.current) {
      return listRefreshInFlightRef.current;
    }
    lastListRefreshAtRef.current = now;
    const run = (async () => {
      try {
        const resp = await apiClient.get<{ code: number; data: TaskSummary[] }>("/rfq/tasks", {
          // Keep every upload visible — same file_name can have multiple tasks.
          params: { limit: 50, unique_file: false },
          silentError: true,
        });
        const rows = resp.data.data || [];
        setRecentTasks(rows);
      } catch {
        // optional UX — never toast from inbox refresh
      } finally {
        listRefreshInFlightRef.current = null;
      }
    })();
    listRefreshInFlightRef.current = run;
    return run;
  }, []);

  const fetchTask = useCallback(
    async (id: string, options?: { broadcast?: boolean }) => {
      const trimmed = id.trim();
      if (!trimmed) return null;
      taskIdRef.current = trimmed;
      setTaskIdState(trimmed);
      setLoading(true);
      try {
        const resp = await apiClient.get<{ code: number; data: TaskPayload }>(
          `/rfq/tasks/${trimmed}`,
          options?.broadcast === false ? { silentError: true } : { showError: true },
        );
        const payload = resp.data.data;
        setTask(payload);
        if (options?.broadcast === false) {
          rememberLastTaskId(trimmed);
        } else {
          notifyTaskChanged(trimmed);
        }
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
    },
    [clearTask],
  );

  const loadTask = useCallback(
    async (rawId?: string) => {
      const id = (rawId ?? taskIdRef.current).trim();
      if (!id) return null;
      return fetchTask(id, { broadcast: true });
    },
    [fetchTask],
  );

  /** Bind context to an already-loaded payload — must not re-broadcast (avoids reload loops). */
  const syncFromPayload = useCallback((payload: TaskPayload) => {
    setTask(payload);
    setTaskIdState(payload.task_id);
    rememberLastTaskId(payload.task_id);
  }, []);

  const setTaskId = useCallback((id: string) => {
    setTaskIdState(id);
  }, []);

  useEffect(() => {
    void refreshRecentTasks({ force: true });
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
      if (!id || id === taskIdRef.current) return;
      // Follow selection without re-broadcasting (page also loads the workspace).
      void fetchTask(id, { broadcast: false });
    };
    window.addEventListener(TASK_CHANGED_EVENT, onChanged);
    return () => window.removeEventListener(TASK_CHANGED_EVENT, onChanged);
  }, [fetchTask]);

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
