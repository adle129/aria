"use client";

import { Button, Card, Form, Input, Typography, message } from "antd";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type ReactNode } from "react";
import { fetchHealth, type HealthData } from "@/api/client";
import { useAuth } from "@/context/AuthContext";

const { Text, Title } = Typography;

const CUSTOMER_NAME = "爱达克车辆设计（上海）有限公司";

function LoginBrandHeader() {
  return (
    <div style={{ textAlign: "center", marginBottom: 32 }}>
      <Text
        strong
        style={{
          display: "block",
          fontSize: 30,
          letterSpacing: 6,
          color: "#E30613",
          lineHeight: 1,
          marginBottom: 10,
        }}
      >
        EDAG
      </Text>
      <Title level={4} style={{ margin: 0, fontWeight: 500, lineHeight: 1.4, color: "#222" }}>
        ARIA · 智能应用平台
      </Title>
      <Text type="secondary" style={{ fontSize: 13, lineHeight: 1.5, letterSpacing: 0.5 }}>
        报价助手
      </Text>
    </div>
  );
}

function LoginForm() {
  const { login, authEnabled, loading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [submitting, setSubmitting] = useState(false);
  const [health, setHealth] = useState<HealthData | null>(null);

  useEffect(() => {
    void fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const onFinish = async (values: { username: string; password: string }) => {
    setSubmitting(true);
    try {
      await login(values.username, values.password);
      message.success("登录成功");
      const next = searchParams.get("next") || "/rfq";
      router.replace(next.startsWith("/") ? next : "/rfq");
    } catch {
      message.error("用户名或密码错误");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return null;
  }

  const cardShell = (children: ReactNode) => (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px 16px",
        background: "linear-gradient(160deg, #F7F7F7 0%, #EFEFEF 100%)",
      }}
    >
      <Card
        style={{
          width: "100%",
          maxWidth: 420,
          borderRadius: 8,
          boxShadow: "0 4px 20px rgba(0,0,0,0.09), 0 1px 4px rgba(0,0,0,0.04)",
        }}
        styles={{ body: { padding: "36px 36px 28px" } }}
      >
        {children}
      </Card>
    </div>
  );

  const footerNote = (
    <Text
      type="secondary"
      style={{
        display: "block",
        textAlign: "center",
        marginTop: 24,
        fontSize: 12,
        lineHeight: 1.6,
        color: "#999",
      }}
    >
      内部系统 · 仅限授权用户访问
      <br />
      <span style={{ fontSize: 11 }}>
        {CUSTOMER_NAME}
        {health?.version ? ` · v${health.version}` : ""}
      </span>
    </Text>
  );

  if (!authEnabled) {
    return cardShell(
      <>
        <LoginBrandHeader />
        <Text type="secondary" style={{ display: "block", textAlign: "center", marginBottom: 20 }}>
          当前环境 AUTH_ENABLED=false，可直接访问业务页面。
        </Text>
        <Button type="primary" block onClick={() => router.replace("/rfq")}>
          进入 RFQ 分析
        </Button>
        {footerNote}
      </>,
    );
  }

  return cardShell(
    <>
      <LoginBrandHeader />
      <Form layout="vertical" onFinish={onFinish} requiredMark={false}>
        <Form.Item name="username" label="用户名" rules={[{ required: true, message: "请输入用户名" }]}>
          <Input autoComplete="username" size="large" placeholder="请输入用户名" />
        </Form.Item>
        <Form.Item name="password" label="密码" rules={[{ required: true, message: "请输入密码" }]}>
          <Input.Password autoComplete="current-password" size="large" placeholder="请输入密码（至少 8 位）" />
        </Form.Item>
        <Button type="primary" htmlType="submit" block size="large" loading={submitting} style={{ marginTop: 8 }}>
          登录
        </Button>
      </Form>
      {footerNote}
    </>,
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
