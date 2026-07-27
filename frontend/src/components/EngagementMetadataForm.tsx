"use client";

import { InfoCircleOutlined } from "@ant-design/icons";
import { Button, Form, Input, Select, Space, Tooltip, Typography, message } from "antd";
import Link from "next/link";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { apiClient, listCustomers, listVehicleModels, type MasterDataItem } from "@/api/client";
import {
  ENGAGEMENT_FUNCTION_OPTIONS,
  engagementYearOptions,
} from "@/lib/engagementMetadata";
import { masterDataSelectOptions } from "@/lib/masterData";
import {
  PROJECT_DISPLAY_NAME_TIP,
  PROJECT_ID_LABEL,
  PROJECT_ID_TIP,
  PROJECT_YEAR_TIP,
} from "@/lib/projectIdentity";

const { Text } = Typography;

export interface EngagementMetadataValue {
  project_name?: string;
  customer?: string | null;
  vehicle_model?: string | null;
  year?: number | null;
  functions?: string[];
}

interface EngagementMetadataFormProps {
  engagementId: string;
  initial?: EngagementMetadataValue;
  disabled?: boolean;
  /** Hide the explanatory alert (parent already shows context). */
  compact?: boolean;
  onSaved?: (next: EngagementMetadataValue & { metadata_complete?: boolean }) => void;
}

function LabelWithTip({ label, tip }: { label: string; tip: ReactNode }) {
  return (
    <span>
      {label}{" "}
      <Tooltip title={tip}>
        <InfoCircleOutlined style={{ color: "#8c8c8c", fontSize: 12 }} />
      </Tooltip>
    </span>
  );
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
  const [customers, setCustomers] = useState<MasterDataItem[]>([]);
  const [vehicleModels, setVehicleModels] = useState<MasterDataItem[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(false);
  const yearOptions = useMemo(() => engagementYearOptions(), []);

  const loadOptions = async () => {
    setLoadingOptions(true);
    try {
      const [c, v] = await Promise.all([listCustomers(false), listVehicleModels(false)]);
      setCustomers(c);
      setVehicleModels(v);
    } catch {
      setCustomers([]);
      setVehicleModels([]);
    } finally {
      setLoadingOptions(false);
    }
  };

  useEffect(() => {
    void loadOptions();
  }, []);

  useEffect(() => {
    form.setFieldsValue({
      project_name: initial?.project_name || engagementId,
      customer: initial?.customer || undefined,
      vehicle_model: initial?.vehicle_model || undefined,
      year: initial?.year ?? undefined,
      functions: initial?.functions || [],
    });
  }, [engagementId, initial, form]);

  const customerOptions = useMemo(() => masterDataSelectOptions(customers), [customers]);
  const vehicleOptions = useMemo(() => masterDataSelectOptions(vehicleModels), [vehicleModels]);

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
        vehicle_model: values.vehicle_model?.trim() || null,
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
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <LabelWithTip label={PROJECT_ID_LABEL} tip={PROJECT_ID_TIP} />
        <Text copyable={{ text: engagementId }} style={{ fontSize: 14, fontWeight: 600 }}>
          {engagementId}
        </Text>
      </div>

      {!compact ? (
        <Text type="secondary" style={{ fontSize: 12 }}>
          客户与车型请先在
          <Link href="/admin/master-data"> 客户与车型 </Link>
          中维护，再在此选择。
        </Text>
      ) : null}

      <Form
        form={form}
        layout="vertical"
        disabled={disabled}
        size={compact ? "small" : "middle"}
        style={{ marginBottom: 0 }}
      >
        <Form.Item
          label={<LabelWithTip label="项目显示名" tip={PROJECT_DISPLAY_NAME_TIP} />}
          name="project_name"
          rules={[{ required: true, whitespace: true, message: "请填写项目显示名" }]}
          style={{ marginBottom: compact ? 10 : 16 }}
        >
          <Input placeholder="如 上海通用汽车 2026 底盘项目" maxLength={256} />
        </Form.Item>
        <Form.Item
          label={
            <LabelWithTip
              label="客户 / 公司"
              tip="用于筛选与对比表头。若列表为空，请先到「客户与车型」添加。"
            />
          }
          name="customer"
          rules={[{ required: true, message: "请选择客户/公司" }]}
          style={{ marginBottom: compact ? 10 : 16 }}
          extra={
            customerOptions.length === 0 ? (
              <Text type="secondary" style={{ fontSize: 12 }}>
                暂无客户，请先在「客户与车型」中添加
              </Text>
            ) : null
          }
        >
          <Select
            showSearch
            allowClear
            loading={loadingOptions}
            placeholder="请选择客户"
            options={customerOptions}
            optionFilterProp="label"
          />
        </Form.Item>
        <Form.Item
          label={
            <LabelWithTip
              label="车型"
              tip="建议填写。同客户可有多套相同车型项目，靠项目编号区分。"
            />
          }
          name="vehicle_model"
          style={{ marginBottom: compact ? 10 : 16 }}
        >
          <Select
            showSearch
            allowClear
            loading={loadingOptions}
            placeholder="请选择车型"
            options={vehicleOptions}
            optionFilterProp="label"
          />
        </Form.Item>
        <Form.Item
          label={<LabelWithTip label="年份" tip={PROJECT_YEAR_TIP} />}
          name="year"
          rules={[{ required: true, message: "请选择年份" }]}
          style={{ marginBottom: compact ? 10 : 16 }}
        >
          <Select
            showSearch
            placeholder="请选择年份"
            options={yearOptions}
            optionFilterProp="label"
          />
        </Form.Item>
        <Form.Item
          label={
            <LabelWithTip label="工程领域" tip="该历史项目覆盖的报价模块，至少选一项。" />
          }
          name="functions"
          rules={[
            {
              required: true,
              type: "array",
              min: 1,
              message: "请至少选择一个工程领域",
            },
          ]}
          style={{ marginBottom: compact ? 10 : 16 }}
        >
          <Select
            mode="tags"
            allowClear
            placeholder="可多选"
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
        保存
      </Button>
    </Space>
  );
}
