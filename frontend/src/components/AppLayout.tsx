"use client";

import {
  DatabaseOutlined,
  FileSearchOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { Layout, Menu, Typography } from "antd";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: "/rfq", icon: <FileSearchOutlined />, label: <Link href="/rfq">RFQ 分析</Link> },
  { key: "/quote", icon: <FileTextOutlined />, label: <Link href="/quote">人力报价</Link> },
  { key: "/knowledge", icon: <DatabaseOutlined />, label: <Link href="/knowledge">知识库</Link> },
];

function selectedKey(pathname: string): string {
  if (pathname.startsWith("/rfq")) return "/rfq";
  if (pathname.startsWith("/quote")) return "/quote";
  if (pathname.startsWith("/knowledge")) return "/knowledge";
  return "/rfq";
}

export default function AppLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

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
          ARIA · 智能报价辅助系统
        </Typography.Title>
        <Typography.Text type="secondary" style={{ marginLeft: 12 }}>
          EDAG 内部工具
        </Typography.Text>
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
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
