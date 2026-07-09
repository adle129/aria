"use client";

import {
  CheckCircleOutlined,
  PauseCircleOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import {
  Badge,
  Button,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  createUser,
  listUsers,
  updateUser,
  type UserDetail,
} from "@/api/client";
import { useAuth } from "@/context/AuthContext";

const { Title } = Typography;

const ROLE_LABELS: Record<string, string> = {
  quote_engineer: "报价工程师",
  kb_admin: "资料库管理员",
};

export default function UserManagePage() {
  const { isKbAdmin, authEnabled, loading } = useAuth();
  const router = useRouter();
  const [users, setUsers] = useState<UserDetail[]>([]);
  const [fetching, setFetching] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm();
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setFetching(true);
    try {
      setUsers(await listUsers());
    } catch {
      message.error("加载用户列表失败");
    } finally {
      setFetching(false);
    }
  }, []);

  useEffect(() => {
    if (!loading && authEnabled && !isKbAdmin) {
      router.replace("/rfq");
    }
  }, [loading, authEnabled, isKbAdmin, router]);

  useEffect(() => {
    if (!loading && isKbAdmin) void load();
  }, [loading, isKbAdmin, load]);

  const handleToggleActive = async (user: UserDetail) => {
    try {
      const updated = await updateUser(user.id, { is_active: !user.is_active });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      message.success(updated.is_active ? "用户已启用" : "用户已停用");
    } catch {
      message.error("操作失败");
    }
  };

  const handleCreate = async () => {
    const values = await createForm.validateFields();
    setCreating(true);
    try {
      const created = await createUser({
        username: values.username as string,
        password: values.password as string,
        display_name: values.display_name as string,
        role: (values.role as string) || "quote_engineer",
      });
      setUsers((prev) => [...prev, created]);
      message.success("用户创建成功");
      createForm.resetFields();
      setCreateOpen(false);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { msg?: string } } })?.response?.data?.msg ?? "创建失败";
      message.error(msg);
    } finally {
      setCreating(false);
    }
  };

  const columns = [
    {
      title: "用户名",
      dataIndex: "username",
      key: "username",
      render: (v: string, r: UserDetail) => (
        <Space>
          <span>{v}</span>
          {!r.is_active && <Tag color="default">已停用</Tag>}
        </Space>
      ),
    },
    {
      title: "显示名",
      dataIndex: "display_name",
      key: "display_name",
    },
    {
      title: "角色",
      dataIndex: "role",
      key: "role",
      render: (v: string) => (
        <Tag color={v === "kb_admin" ? "blue" : "default"}>{ROLE_LABELS[v] ?? v}</Tag>
      ),
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (v: string | null) =>
        v ? new Date(v).toLocaleDateString("zh-CN") : "—",
    },
    {
      title: "状态",
      key: "is_active",
      render: (_: unknown, r: UserDetail) => (
        <Badge
          status={r.is_active ? "success" : "default"}
          text={r.is_active ? "正常" : "停用"}
        />
      ),
    },
    {
      title: "操作",
      key: "action",
      render: (_: unknown, r: UserDetail) => (
        <Space>
          <Switch
            size="small"
            checked={r.is_active}
            checkedChildren={<CheckCircleOutlined />}
            unCheckedChildren={<PauseCircleOutlined />}
            onChange={() => void handleToggleActive(r)}
          />
        </Space>
      ),
    },
  ];

  if (loading || !isKbAdmin) return null;

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", alignItems: "center", marginBottom: 16, gap: 12 }}>
        <Title level={4} style={{ margin: 0 }}>
          用户管理
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          size="small"
          onClick={() => setCreateOpen(true)}
        >
          新建用户
        </Button>
      </div>

      <Table
        rowKey="id"
        dataSource={users}
        columns={columns}
        loading={fetching}
        pagination={false}
        size="small"
        style={{ maxWidth: 800 }}
      />

      <Modal
        title="新建用户"
        open={createOpen}
        onOk={() => void handleCreate()}
        onCancel={() => {
          createForm.resetFields();
          setCreateOpen(false);
        }}
        okText="创建"
        cancelText="取消"
        confirmLoading={creating}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: "请输入用户名" }]}
          >
            <Input placeholder="英文/数字，不可重复" autoComplete="off" />
          </Form.Item>
          <Form.Item
            name="display_name"
            label="显示名"
            rules={[{ required: true, message: "请输入显示名" }]}
          >
            <Input placeholder="如：张工" />
          </Form.Item>
          <Form.Item
            name="password"
            label="初始密码"
            rules={[
              { required: true, message: "请输入初始密码" },
              { min: 8, message: "至少 8 位" },
            ]}
          >
            <Input.Password placeholder="至少 8 位，用户登录后可自行修改" />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="quote_engineer">
            <Select>
              <Select.Option value="quote_engineer">报价工程师</Select.Option>
              <Select.Option value="kb_admin">资料库管理员</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
