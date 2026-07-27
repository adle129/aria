"use client";

import { DeleteOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  createCustomer,
  createVehicleModel,
  deleteCustomer,
  deleteVehicleModel,
  listCustomers,
  listVehicleModels,
  updateCustomer,
  updateVehicleModel,
  type MasterDataItem,
} from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import { ADMIN_NAV_LABELS } from "@/lib/adminNav";

const { Title, Paragraph } = Typography;

type Kind = "customers" | "vehicles";

function apiErrorMessage(err: unknown, fallback: string): string {
  return (
    (err as { response?: { data?: { msg?: string } } })?.response?.data?.msg ?? fallback
  );
}

export default function MasterDataPage() {
  const { isKbAdmin, authEnabled, loading } = useAuth();
  const router = useRouter();
  const [kind, setKind] = useState<Kind>("customers");
  const [rows, setRows] = useState<MasterDataItem[]>([]);
  const [fetching, setFetching] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [editRow, setEditRow] = useState<MasterDataItem | null>(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const canManage = !authEnabled || isKbAdmin;

  const load = useCallback(async () => {
    setFetching(true);
    try {
      const data =
        kind === "customers"
          ? await listCustomers(true)
          : await listVehicleModels(true);
      setRows(data);
    } catch {
      message.error("加载主数据失败");
      setRows([]);
    } finally {
      setFetching(false);
    }
  }, [kind]);

  useEffect(() => {
    if (!loading && authEnabled && !isKbAdmin) {
      router.replace("/rfq");
    }
  }, [loading, authEnabled, isKbAdmin, router]);

  useEffect(() => {
    if (!loading && canManage) void load();
  }, [loading, canManage, load]);

  const handleToggle = async (row: MasterDataItem) => {
    try {
      const updated =
        kind === "customers"
          ? await updateCustomer(row.id, { is_active: !row.is_active })
          : await updateVehicleModel(row.id, { is_active: !row.is_active });
      setRows((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      message.success(updated.is_active ? "已启用" : "已停用");
    } catch (err) {
      message.error(apiErrorMessage(err, "操作失败"));
    }
  };

  const handleCreate = async () => {
    const values = await createForm.validateFields();
    setSaving(true);
    try {
      const name = String(values.name || "").trim();
      if (kind === "customers") {
        await createCustomer(name);
      } else {
        await createVehicleModel(name);
      }
      message.success("已添加");
      createForm.resetFields();
      setCreateOpen(false);
      await load();
    } catch (err: unknown) {
      message.error(apiErrorMessage(err, "创建失败"));
    } finally {
      setSaving(false);
    }
  };

  const openEdit = (row: MasterDataItem) => {
    setEditRow(row);
    editForm.setFieldsValue({ name: row.name });
  };

  const handleEdit = async () => {
    if (!editRow) return;
    const values = await editForm.validateFields();
    setSaving(true);
    try {
      const name = String(values.name || "").trim();
      const updated =
        kind === "customers"
          ? await updateCustomer(editRow.id, { name })
          : await updateVehicleModel(editRow.id, { name });
      const n = updated.renamed_engagements ?? 0;
      message.success(n > 0 ? `已重命名，并同步 ${n} 个历史项目` : "已保存");
      setEditRow(null);
      await load();
    } catch (err: unknown) {
      message.error(apiErrorMessage(err, "保存失败"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (row: MasterDataItem) => {
    try {
      if (kind === "customers") {
        await deleteCustomer(row.id);
      } else {
        await deleteVehicleModel(row.id);
      }
      message.success("已删除");
      await load();
    } catch (err: unknown) {
      message.error(apiErrorMessage(err, "删除失败"));
    }
  };

  if (loading) return null;
  if (authEnabled && !isKbAdmin) return null;

  const noun = kind === "customers" ? "客户" : "车型";

  return (
    <div>
      <Title level={3}>{ADMIN_NAV_LABELS.masterData}</Title>
      <Paragraph type="secondary">
        维护客户/公司与车型主数据。填写历史项目信息时从列表选择；重命名会同步已绑定项目；删除仅在无项目引用时允许，否则请先改绑或停用。
      </Paragraph>

      <Card size="small">
        <Tabs
          activeKey={kind}
          onChange={(key) => setKind(key as Kind)}
          tabBarExtraContent={
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                createForm.resetFields();
                setCreateOpen(true);
              }}
            >
              添加{noun}
            </Button>
          }
          items={[
            { key: "customers", label: "客户 / 公司" },
            { key: "vehicles", label: "车型" },
          ]}
        />
        <Table
          rowKey="id"
          size="small"
          loading={fetching}
          dataSource={rows}
          pagination={false}
          columns={[
            { title: "名称", dataIndex: "name" },
            {
              title: "状态",
              dataIndex: "is_active",
              width: 100,
              render: (active: boolean) =>
                active ? <Tag color="success">启用</Tag> : <Tag>停用</Tag>,
            },
            {
              title: "启用",
              width: 88,
              render: (_, row) => (
                <Switch checked={row.is_active} onChange={() => void handleToggle(row)} />
              ),
            },
            {
              title: "操作",
              width: 160,
              render: (_, row) => (
                <Space size={4}>
                  <Button
                    type="link"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => openEdit(row)}
                  >
                    编辑
                  </Button>
                  <Popconfirm
                    title={`删除${noun}「${row.name}」？`}
                    description="仅当没有历史项目引用时可删除。"
                    okText="删除"
                    okButtonProps={{ danger: true }}
                    cancelText="取消"
                    onConfirm={() => void handleDelete(row)}
                  >
                    <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={`添加${noun}`}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => void handleCreate()}
        confirmLoading={saving}
        okText="添加"
        destroyOnClose
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="name"
            label={`${noun}名称`}
            rules={[{ required: true, whitespace: true, message: `请输入${noun}名称` }]}
          >
            <Input maxLength={256} placeholder={kind === "customers" ? "如 上海通用" : "如 MEB"} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`编辑${noun}`}
        open={Boolean(editRow)}
        onCancel={() => setEditRow(null)}
        onOk={() => void handleEdit()}
        confirmLoading={saving}
        okText="保存"
        destroyOnClose
      >
        <Form form={editForm} layout="vertical">
          <Form.Item
            name="name"
            label={`${noun}名称`}
            rules={[{ required: true, whitespace: true, message: `请输入${noun}名称` }]}
            extra="重命名后会同步已绑定该名称的历史项目。"
          >
            <Input maxLength={256} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
