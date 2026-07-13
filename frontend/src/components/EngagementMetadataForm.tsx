"use client";

import { Alert, Button, Form, Input, Select, Space, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { apiClient } from "@/api/client";
import {
  ENGAGEMENT_FUNCTION_OPTIONS,
  engagementYearOptions,
} from "@/lib/engagementMetadata";

export interface EngagementMetadataValue {
  project_name?: string;
  customer?: string | null;
  year?: number | null;
  functions?: string[];
}

interface EngagementMetadataFormProps {
  engagementId: string;
  initial?: EngagementMetadataValue;
  disabled?: boolean;
  compact?: boolean;
  onSaved?: (next: EngagementMetadataValue & { metadata_complete?: boolean }) => void;
}

export default function EngagementMetadataForm({
  engagementId,
  initial,
  disabled = false,
  compact = false,
  onSaved,
}: EngagementMetadataFormProps) {
  const [form] = Form.useForm<EngagementMetadataValue>();
  const [saving, setSaving] = useState(false);
  const yearOptions = useMemo(() => engagementYearOptions(), []);

  useEffect(() => {
    form.setFieldsValue({
      project_name: initial?.project_name || engagementId,
      customer: initial?.customer || undefined,
      year: initial?.year ?? undefined,
      functions: initial?.functions || [],
    });
  }, [engagementId, initial, form]);

  const handleSave = async () => {
    if (disabled) return;
    try {
      const values = await form.validateFields();
      setSaving(true);
      const resp = await apiClient.patch<{
        code: number;
        data: EngagementMetadataValue & { metadata_complete?: boolean };
      }>(`/knowledge/engagements/${encodeURIComponent(engagementId)}/metadata`, {
        project_name: values.project_name?.trim(),
        customer: values.customer?.trim(),
        year: values.year,
        functions: values.functions || [],
      });
      message.success("项目信息已保存");
      onSaved?.(resp.data.data);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Space direction="vertical" size={compact ? 8 : 12} style={{ width: "100%" }}>
      {!compact && (
        <Alert
          type="info"
          showIcon
          message="请完善项目信息"
          description="项目显示名、客户、年份、工程领域均为必填。保存后更新索引，工程领域才会写入检索过滤。"
        />
      )}
      <Form form={form} layout="vertical" disabled={disabled} style={{ marginBottom: 0 }}>
        <Form.Item
          label="项目显示名"
          name="project_name"
          rules={[{ required: true, whitespace: true, message: "请填写项目显示名" }]}
        >
          <Input placeholder="如 2024 Chassis Integration" maxLength={256} />
        </Form.Item>
        <Form.Item
          label="客户"
          name="customer"
          rules={[{ required: true, whitespace: true, message: "请填写客户" }]}
        >
          <Input placeholder="如 OEM-A" maxLength={256} />
        </Form.Item>
        <Form.Item
          label="年份"
          name="year"
          rules={[{ required: true, message: "请选择年份" }]}
        >
          <Select
            showSearch
            placeholder="请选择年份"
            options={yearOptions}
            optionFilterProp="label"
          />
        </Form.Item>
        <Form.Item
          label="工程领域"
          name="functions"
          rules={[
            {
              required: true,
              type: "array",
              min: 1,
              message: "请至少选择一个工程领域",
            },
          ]}
        >
          <Select
            mode="tags"
            allowClear
            placeholder="可多选或自定义"
            options={ENGAGEMENT_FUNCTION_OPTIONS.map((value) => ({
              value,
              label: value,
            }))}
          />
        </Form.Item>
      </Form>
      <Button
        type="primary"
        loading={saving}
        disabled={disabled}
        onClick={() => void handleSave()}
      >
        保存项目信息
      </Button>
    </Space>
  );
}
