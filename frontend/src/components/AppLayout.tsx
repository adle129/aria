"use client";

import {
  BugOutlined,
  BulbOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  KeyOutlined,
  LogoutOutlined,
  QuestionCircleOutlined,
  SearchOutlined,
  UserOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { Alert, Button, Dropdown, Input, Layout, Menu, Pagination, Segmented, Space, Tag, Typography, message, type MenuProps } from "antd";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { archiveTask, deleteTask, fetchHealth, type HealthData } from "@/api/client";
import RfqRecentTasksTable from "@/components/rfq/RfqRecentTasksTable";
import TaskContextBar from "@/components/TaskContextBar";
import ChangePasswordModal from "@/components/ChangePasswordModal";
import { AuthProvider, useAuth, useTokenExpiryWarning } from "@/context/AuthContext";
import { TaskProvider, useTaskContext } from "@/context/TaskContext";
import { useUiProfile } from "@/hooks/useUiProfile";
import {
  getStepMilestone,
  isQuotingStepDelivered,
  isR1Profile,
  isTaskContextBarVisible,
  resolveUiProfile,
  shouldBlockPath,
  showDemoChrome,
  type UiProfile,
} from "@/lib/uiProfile";
import { RFQ_BEGIN_NEW_EVENT, RFQ_BEGIN_NEW_FLAG } from "@/lib/rfqWorkspace";
import { matchesInboxFilter, type InboxFilterKey } from "@/lib/taskStatus";

const { Header, Sider, Content } = Layout;

const QUOTING_STEP_DEFS = [
  { step: "rfq" as const, key: "/rfq", icon: <FileSearchOutlined />, title: "RFQ 分析" },
  { step: "proposal" as const, key: "/proposal", icon: <BulbOutlined />, title: "方案草案" },
  { step: "qa" as const, key: "/qa", icon: <QuestionCircleOutlined />, title: "QA 清单" },
  { step: "quote" as const, key: "/quote", icon: <FileTextOutlined />, title: "人力报价" },
] as const;

function buildQuotingMenuChildren(profile: UiProfile) {
  return QUOTING_STEP_DEFS.map(({ step, key, icon, title }) => {
    const delivered = isQuotingStepDelivered(profile, step);
    const milestone = getStepMilestone(step);

    if (delivered) {
      return {
        key,
        icon,
        label: step === "rfq" ? title : <Link href={key}>{title}</Link>,
      };
    }

    return {
      key,
      icon,
      disabled: true,
      label: (
        <span style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{title}</span>
          {milestone && (
            <span style={{ fontSize: 10, color: "#bfbfbf", fontWeight: 500, letterSpacing: 0.3 }}>
              {milestone}
            </span>
          )}
        </span>
      ),
    };
  });
}

function buildPlatformKnowledgeChildren(profile: UiProfile, health: HealthData | null) {
  const items = [
    {
      key: "/knowledge",
      icon: <DatabaseOutlined />,
      label: <Link href="/knowledge">知识库</Link>,
    },
  ];
  if (profile === "dev" && health?.kb_debug_enabled) {
    items.push({
      key: "/knowledge/debug",
      icon: <BugOutlined />,
      label: <Link href="/knowledge/debug">知识库 · Debug</Link>,
    });
  }
  return items;
}

function buildMenuItems(profile: UiProfile, health: HealthData | null) {
  return [
    {
      type: "group" as const,
      label: "应用 · 报价流程",
      children: buildQuotingMenuChildren(profile),
    },
    {
      type: "group" as const,
      label: "平台 · 知识库",
      children: buildPlatformKnowledgeChildren(profile, health),
    },
  ];
}

function selectedKey(pathname: string): string {
  if (pathname.startsWith("/knowledge/debug")) return "/knowledge/debug";
  if (pathname.startsWith("/proposal")) return "/proposal";
  if (pathname.startsWith("/qa")) return "/qa";
  if (pathname.startsWith("/rfq")) return "/rfq";
  if (pathname.startsWith("/quote")) return "/quote";
  if (pathname.startsWith("/knowledge")) return "/knowledge";
  return "/rfq";
}

function ModeBadge({ health, formalDelivery }: { health: HealthData | null; formalDelivery: boolean }) {
  if (!health) return null;
  if (health.mock_llm) {
    return formalDelivery ? (
      <Tag color="red">LLM 配置异常</Tag>
    ) : (
      <Tag color="default">Mock LLM</Tag>
    );
  }
  if (!health.ollama_reachable) {
    return <Tag color="red">LLM 未连接</Tag>;
  }
  if (!health.ollama_model_ready) {
    return <Tag color="orange">模型未就绪</Tag>;
  }
  return <Tag color="green">LLM: {health.model}</Tag>;
}

function RfqSideInbox({ pathname }: { pathname: string }) {
  const router = useRouter();
  const { recentTasks, task, loading, loadTask, refreshRecentTasks } = useTaskContext();
  const [openingTaskId, setOpeningTaskId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filterKey, setFilterKey] = useState<InboxFilterKey>("all");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 8;
  const showInbox = pathname.startsWith("/rfq");

  useEffect(() => {
    if (!showInbox) return;
    void refreshRecentTasks();
  }, [showInbox, refreshRecentTasks]);

  const filteredTasks = useMemo(() => {
    const q = query.trim().toLowerCase();
    return recentTasks.filter((t) => {
      if (!matchesInboxFilter(t.processing_status, filterKey)) return false;
      if (!q) return true;
      const shortId = t.task_id.slice(0, 8);
      const merged = [
        t.file_name,
        t.project_name || "",
        t.customer || "",
        t.task_id,
        shortId,
      ]
        .join(" ")
        .toLowerCase();
      return merged.includes(q);
    });
  }, [recentTasks, filterKey, query]);

  const pagedTasks = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filteredTasks.slice(start, start + PAGE_SIZE);
  }, [filteredTasks, page]);

  useEffect(() => {
    setPage(1);
  }, [query, filterKey]);

  useEffect(() => {
    const maxPage = Math.max(1, Math.ceil(filteredTasks.length / PAGE_SIZE));
    if (page > maxPage) setPage(maxPage);
  }, [filteredTasks.length, page]);

  if (!showInbox) return null;

  const openTask = async (taskId: string) => {
    setOpeningTaskId(taskId);
    try {
      await loadTask(taskId);
      router.push("/rfq");
    } finally {
      setOpeningTaskId(null);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    try {
      await deleteTask(taskId);
      message.success("任务已删除");
      void refreshRecentTasks();
    } catch {
      // error shown by interceptor
    }
  };

  const handleArchiveTask = async (taskId: string) => {
    try {
      await archiveTask(taskId);
      message.success("任务已归档");
      void refreshRecentTasks();
    } catch {
      // error shown by interceptor
    }
  };

  return (
    <div
      style={{
        borderTop: "1px solid #f0f0f0",
        marginTop: 8,
        paddingTop: 8,
        display: "flex",
        flexDirection: "column",
        minHeight: 0,
        flex: 1,
      }}
    >
      <div style={{ padding: "0 10px 8px" }}>
        <Typography.Text
          type="secondary"
          style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.4, textTransform: "uppercase", display: "block", marginBottom: 6 }}
        >
          最近 RFQ
        </Typography.Text>
        <Input
          allowClear
          size="small"
          prefix={<SearchOutlined style={{ color: "#BFBFBF" }} />}
          placeholder="搜索文件名 / 项目 / 客户"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <Segmented
          size="small"
          value={filterKey}
          onChange={(v) => setFilterKey(v as InboxFilterKey)}
          options={[
            { label: "全部", value: "all" },
            { label: "进行中", value: "in_progress" },
            { label: "已完成", value: "done" },
            { label: "失败", value: "failed" },
          ]}
          style={{ marginTop: 8, width: "100%", fontSize: 11 }}
        />
        {filteredTasks.length !== recentTasks.length && (
          <Typography.Text type="secondary" style={{ fontSize: 11, marginTop: 6, display: "block" }}>
            {filteredTasks.length} / {recentTasks.length} 条
          </Typography.Text>
        )}
      </div>
      <div style={{ overflowY: "auto", minHeight: 0, flex: 1 }}>
        <RfqRecentTasksTable
          tasks={pagedTasks}
          activeTaskId={task?.task_id}
          loading={loading || openingTaskId !== null}
          onOpen={(id) => void openTask(id)}
          onDelete={(id) => void handleDeleteTask(id)}
          onArchive={(id) => void handleArchiveTask(id)}
        />
      </div>
      {filteredTasks.length > PAGE_SIZE && (
        <div style={{ borderTop: "1px solid #f0f0f0", padding: "8px 10px 10px" }}>
          <Pagination
            simple
            size="small"
            current={page}
            pageSize={PAGE_SIZE}
            total={filteredTasks.length}
            onChange={(p) => setPage(p)}
          />
        </div>
      )}
    </div>
  );
}

function AppLayoutInner({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { loading: authLoading, authEnabled, user, logout } = useAuth();
  const [pwModalOpen, setPwModalOpen] = useState(false);
  const minsUntilExpiry = useTokenExpiryWarning();
  const [health, setHealth] = useState<HealthData | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const profile = resolveUiProfile(health?.aria_ui_profile);
  const formalDelivery = !showDemoChrome(profile);

  useEffect(() => {
    if (pathname.startsWith("/login")) return;
    if (authLoading) return;
    if (authEnabled && !user) {
      const next = encodeURIComponent(pathname);
      router.replace(`/login?next=${next}`);
    }
  }, [authLoading, authEnabled, user, pathname, router]);

  useEffect(() => {
    if (pathname.startsWith("/login")) return;
    if (shouldBlockPath(profile, pathname)) {
      router.replace("/rfq");
    }
  }, [profile, pathname, router]);

  if (pathname.startsWith("/login")) {
    return <>{children}</>;
  }

  if (authEnabled && authLoading) {
    return null;
  }

  if (shouldBlockPath(profile, pathname)) {
    return null;
  }

  const isKbAdmin = user?.role === "kb_admin";
  const menuItems = [
    ...buildMenuItems(profile, health),
    ...(authEnabled && isKbAdmin
      ? [
          {
            type: "group" as const,
            label: "管理",
            children: [
              {
                key: "/admin/users",
                icon: <UserOutlined />,
                label: <Link href="/admin/users">用户管理</Link>,
              },
            ],
          },
        ]
      : []),
  ];
  const showTaskContextBar = isTaskContextBarVisible(pathname);
  const siderWidth = pathname.startsWith("/rfq") ? 280 : 200;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          padding: "0 24px",
          borderBottom: "1px solid #eee",
          background: "#fff",
        }}
      >
        <Typography.Text
          strong
          style={{ fontSize: 18, letterSpacing: 2, color: "#E30613", marginRight: 16 }}
        >
          EDAG
        </Typography.Text>
        <Typography.Title level={4} style={{ margin: 0, fontWeight: 500 }}>
          ARIA · 智能应用平台
        </Typography.Title>
        <Tag color="processing" style={{ marginLeft: 12 }}>
          报价助手
        </Tag>
        {isR1Profile(profile) && (
          <Tag color="blue" style={{ marginLeft: 8 }}>
            R1
          </Tag>
        )}
        <Typography.Text type="secondary" style={{ marginLeft: 12 }}>
          EDAG 内部工具
        </Typography.Text>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <ModeBadge health={health} formalDelivery={formalDelivery} />
          {health?.mock_rag && !formalDelivery && <Tag>Mock RAG</Tag>}
          {health?.mock_rag && formalDelivery && <Tag color="red">RAG 配置异常</Tag>}
          {authEnabled && user && (
            <Space size={8}>
              {minsUntilExpiry !== null && minsUntilExpiry <= 30 && minsUntilExpiry > 0 && (
                <Tag icon={<WarningOutlined />} color="warning">
                  登录将在 {minsUntilExpiry} 分钟后过期
                </Tag>
              )}
              {user.role === "kb_admin" && <Tag color="blue">资料库管理员</Tag>}
              <Dropdown
                menu={{
                  items: [
                    {
                      key: "change-password",
                      icon: <KeyOutlined />,
                      label: "修改密码",
                      onClick: () => setPwModalOpen(true),
                    },
                    { type: "divider" },
                    {
                      key: "logout",
                      icon: <LogoutOutlined />,
                      label: "退出登录",
                      danger: true,
                      onClick: () => void logout(),
                    },
                  ] satisfies MenuProps["items"],
                }}
                trigger={["click"]}
              >
                <Button type="text" size="small" icon={<UserOutlined />}>
                  {user.display_name || user.username}
                </Button>
              </Dropdown>
              <ChangePasswordModal open={pwModalOpen} onClose={() => setPwModalOpen(false)} />
            </Space>
          )}
        </div>
      </Header>
      <Layout>
        <Sider
          width={siderWidth}
          theme="light"
          style={{ borderRight: "1px solid #eee", display: "flex", flexDirection: "column" }}
        >
          <Menu
            mode="inline"
            selectedKeys={[selectedKey(pathname)]}
            items={menuItems}
            style={{ borderRight: 0 }}
            onClick={({ key }) => {
              if (key !== "/rfq") return;
              if (typeof window !== "undefined") {
                sessionStorage.setItem(RFQ_BEGIN_NEW_FLAG, "1");
                window.dispatchEvent(new CustomEvent(RFQ_BEGIN_NEW_EVENT));
              }
              if (!pathname.startsWith("/rfq")) {
                router.push("/rfq");
              }
            }}
          />
          <RfqSideInbox pathname={pathname} />
        </Sider>
        <Content style={{ margin: 24, padding: 24, background: "#fff", borderRadius: 4 }}>
          {showTaskContextBar && <TaskContextBar />}
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <TaskProvider>
        <AppLayoutInner>{children}</AppLayoutInner>
      </TaskProvider>
    </AuthProvider>
  );
}
