"use client";

import { Button, Card, Form, Input, Typography, message } from "antd";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useAuth } from "@/context/AuthContext";

const { Title, Paragraph } = Typography;

function LoginForm() {
  const { login, authEnabled, loading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [submitting, setSubmitting] = useState(false);

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

  if (!authEnabled) {
    return (
      <Card style={{ maxWidth: 420, margin: "80px auto" }}>
        <Title level={4}>认证未启用</Title>
        <Paragraph type="secondary">当前环境 AUTH_ENABLED=false，可直接访问业务页面。</Paragraph>
        <Button type="primary" onClick={() => router.replace("/rfq")}>
          进入 RFQ 分析
        </Button>
      </Card>
    );
  }

  return (
    <Card style={{ maxWidth: 420, margin: "80px auto" }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        ARIA 登录
      </Title>
      <Form layout="vertical" onFinish={onFinish}>
        <Form.Item name="username" label="用户名" rules={[{ required: true, message: "请输入用户名" }]}>
          <Input autoComplete="username" />
        </Form.Item>
        <Form.Item name="password" label="密码" rules={[{ required: true, message: "请输入密码" }]}>
          <Input.Password autoComplete="current-password" />
        </Form.Item>
        <Button type="primary" htmlType="submit" block loading={submitting}>
          登录
        </Button>
      </Form>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
