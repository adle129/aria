"use client";

import { Form, Input, Modal, message } from "antd";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function ChangePasswordModal({ open, onClose }: Props) {
  const { changePassword } = useAuth();
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const handleOk = async () => {
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      await changePassword(values.old_password as string, values.new_password as string);
      message.success("密码修改成功");
      form.resetFields();
      onClose();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { msg?: string } } })?.response?.data?.msg ?? "修改失败，请重试";
      message.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title="修改密码"
      open={open}
      onOk={() => void handleOk()}
      onCancel={() => {
        form.resetFields();
        onClose();
      }}
      okText="确认修改"
      cancelText="取消"
      confirmLoading={submitting}
      destroyOnClose
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item
          name="old_password"
          label="当前密码"
          rules={[{ required: true, message: "请输入当前密码" }]}
        >
          <Input.Password placeholder="请输入当前密码" />
        </Form.Item>
        <Form.Item
          name="new_password"
          label="新密码"
          rules={[
            { required: true, message: "请输入新密码" },
            { min: 8, message: "密码至少 8 位" },
          ]}
        >
          <Input.Password placeholder="至少 6 位" />
        </Form.Item>
        <Form.Item
          name="confirm_password"
          label="确认新密码"
          dependencies={["new_password"]}
          rules={[
            { required: true, message: "请再次输入新密码" },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue("new_password") === value) {
                  return Promise.resolve();
                }
                return Promise.reject(new Error("两次输入的密码不一致"));
              },
            }),
          ]}
        >
          <Input.Password placeholder="再次输入新密码" />
        </Form.Item>
      </Form>
    </Modal>
  );
}
