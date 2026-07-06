"use client";

import {
  BugOutlined,
  BulbOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
} from "@ant-design/icons";
import { Layout, Menu, Tag, Typography } from "antd";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { fetchHealth, type HealthData } from "@/api/client";
import TaskContextBar from "@/components/TaskContextBar";
import { TaskProvider } from "@/context/TaskContext";

const { Header, Sider, Content } = Layout;

const UI_PROFILE = process.env.NEXT_PUBLIC_ARIA_UI_PROFILE || "experience";

function buildPlatformKnowledgeChildren(health: HealthData | null) {
  const items = [
    {
      key: "/knowledge",
      icon: <DatabaseOutlined />,
      label: <Link href="/knowledge">知识库</Link>,
    },
  ];
  const profile = health?.aria_ui_profile || UI_PROFILE;
  if (profile === "dev" && health?.kb_debug_enabled) {
    items.push({
      key: "/knowledge/debug",
      icon: <BugOutlined />,
      label: <Link href="/knowledge/debug">知识库 · Debug</Link>,
    });
  }
  return items;
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

function ModeBadge({ health }: { health: HealthData | null }) {
  if (!health) return null;
  if (health.mock_llm) {
    return <Tag color="default">Mock LLM</Tag>;
  }
  if (!health.ollama_reachable) {
    return <Tag color="red">LLM 未连接</Tag>;
  }
  if (!health.ollama_model_ready) {
    return <Tag color="orange">模型未就绪</Tag>;
  }
  return <Tag color="green">LLM: {health.model}</Tag>;
}

function AppLayoutInner({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [health, setHealth] = useState<HealthData | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const menuItems = [
    {
      type: "group" as const,
      label: "应用 · 报价流程",
      children: [
        { key: "/rfq", icon: <FileSearchOutlined />, label: <Link href="/rfq">RFQ 分析</Link> },
        { key: "/proposal", icon: <BulbOutlined />, label: <Link href="/proposal">方案草案</Link> },
        { key: "/qa", icon: <QuestionCircleOutlined />, label: <Link href="/qa">QA 清单</Link> },
        { key: "/quote", icon: <FileTextOutlined />, label: <Link href="/quote">人力报价</Link> },
      ],
    },
    {
      type: "group" as const,
      label: "平台 · 知识库",
      children: buildPlatformKnowledgeChildren(health),
    },
  ];

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
        <Typography.Text type="secondary" style={{ marginLeft: 12 }}>
          EDAG 内部工具
        </Typography.Text>
        <div style={{ marginLeft: "auto" }}>
          <ModeBadge health={health} />
          {health?.mock_rag && <Tag style={{ marginLeft: 8 }}>Mock RAG</Tag>}
        </div>
      </Header>
      <Layout>
        <Sider width={200} theme="light" style={{ borderRight: "1px solid #eee" }}>
          <Menu
            mode="inline"
            selectedKeys={[selectedKey(pathname)]}
            items={menuItems}
            style={{ height: "100%", borderRight: 0 }}
          />
        </Sider>
        <Content style={{ margin: 24, padding: 24, background: "#fff", borderRadius: 4 }}>
          <TaskContextBar />
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <TaskProvider>
      <AppLayoutInner>{children}</AppLayoutInner>
    </TaskProvider>
  );
}
