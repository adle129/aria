"use client";

import { InfoCircleOutlined } from "@ant-design/icons";
import {
  Alert,
  Card,
  Col,
  Divider,
  Progress,
  Row,
  Space,
  Spin,
  Statistic,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { useRouter } from "next/navigation";
import {
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import {
  apiClient,
  fetchHealth,
  listUsers,
  type HealthData,
  type UserDetail,
} from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import {
  ADMIN_NAV_LABELS,
  aiHealthTagColor,
  canAccessAdminOpsNav,
  canAccessUserAdmin,
  summarizeAiHealth,
} from "@/lib/adminNav";

const { Title, Text } = Typography;

type KnowledgeStats = {
  total_documents?: number;
  total_chunks?: number;
  total_projects?: number;
  last_import_at?: string | null;
  function_coverage?: Record<string, number>;
  mock_rag?: boolean;
};

type EngagementRow = {
  engagement_id: string;
  metadata_complete?: boolean;
  index_status?: string;
};

const ROLE_LABEL: Record<string, string> = {
  quote_engineer: "报价工程师",
  kb_admin: "资料库管理员",
};

const STAT_TITLE_STYLE = { fontSize: 14, color: "rgba(0,0,0,0.65)", fontWeight: 500 };
const STAT_VALUE_STYLE = { fontSize: 28, fontWeight: 600 };
const SECTION_GAP = 20;
const BODY = 14;

function formatBytes(n?: number): string {
  if (n == null || Number.isNaN(n)) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(2)} GB`;
}

function formatTime(iso?: string | null): string {
  if (!iso) return "尚未更新";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return iso;
  return new Date(t).toLocaleString("zh-CN");
}

function Tip({ title }: { title: ReactNode }) {
  return (
    <Tooltip title={title}>
      <InfoCircleOutlined
        style={{ color: "rgba(0,0,0,0.45)", marginLeft: 6, cursor: "help" }}
      />
    </Tooltip>
  );
}

function Section({
  title,
  tip,
  extra,
  children,
}: {
  title: string;
  tip?: ReactNode;
  extra?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div style={{ marginBottom: SECTION_GAP }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          marginBottom: 10,
          flexWrap: "wrap",
        }}
      >
        <span>
          <Text strong style={{ fontSize: 16 }}>
            {title}
          </Text>
          {tip ? <Tip title={tip} /> : null}
        </span>
        {extra}
      </div>
      {children}
    </div>
  );
}

function Metric({
  title,
  value,
  tip,
  valueStyle,
}: {
  title: string;
  value: string | number;
  tip?: ReactNode;
  valueStyle?: CSSProperties;
}) {
  return (
    <Statistic
      title={
        <span style={STAT_TITLE_STYLE}>
          {title}
          {tip ? <Tip title={tip} /> : null}
        </span>
      }
      value={value}
      valueStyle={{ ...STAT_VALUE_STYLE, ...valueStyle }}
    />
  );
}

const CARD_STYLES = {
  body: { paddingTop: 16, paddingBottom: 16 },
};

/** Admin home: concise grouped dashboard; explanations live in tooltips. */
export default function AdminOverviewPage() {
  const { loading, authEnabled, isKbAdmin, user } = useAuth();
  const router = useRouter();
  const [health, setHealth] = useState<HealthData | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [engagements, setEngagements] = useState<EngagementRow[]>([]);
  const [users, setUsers] = useState<UserDetail[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  const allowed = canAccessAdminOpsNav({ authEnabled, isKbAdmin });
  const canLoadUsers = canAccessUserAdmin({ authEnabled, isKbAdmin });

  useEffect(() => {
    if (loading) return;
    if (!allowed) {
      router.replace("/rfq");
    }
  }, [loading, allowed, router]);

  useEffect(() => {
    if (!allowed) return;
    let cancelled = false;
    setLoadingData(true);
    void (async () => {
      try {
        const [h, statsResp, engResp, userList] = await Promise.all([
          fetchHealth().catch(() => null),
          apiClient
            .get<{ code: number; data: KnowledgeStats }>("/knowledge/stats")
            .then((r) => r.data.data)
            .catch(() => null),
          apiClient
            .get<{ code: number; data: { engagements: EngagementRow[] } }>(
              "/knowledge/engagements",
            )
            .then((r) => r.data.data.engagements ?? [])
            .catch(() => [] as EngagementRow[]),
          canLoadUsers ? listUsers().catch(() => [] as UserDetail[]) : Promise.resolve([]),
        ]);
        if (cancelled) return;
        setHealth(h);
        setHealthError(!h);
        setStats(statsResp);
        setEngagements(engResp);
        setUsers(userList);
      } finally {
        if (!cancelled) setLoadingData(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [allowed, canLoadUsers]);

  const ai = useMemo(
    () => summarizeAiHealth(healthError ? null : health),
    [health, healthError],
  );

  const kbHealth = useMemo(() => {
    const incomplete = engagements.filter((e) => e.metadata_complete === false).length;
    const failed = engagements.filter((e) => e.index_status === "failed").length;
    const pending = engagements.filter((e) => e.index_status === "pending").length;
    const indexed = engagements.filter((e) => e.index_status === "indexed").length;
    return { incomplete, failed, pending, indexed, total: engagements.length };
  }, [engagements]);

  const userSummary = useMemo(() => {
    const engineers = users.filter((u) => u.role === "quote_engineer").length;
    const admins = users.filter((u) => u.role === "kb_admin").length;
    const inactive = users.filter((u) => !u.is_active).length;
    return { engineers, admins, inactive, total: users.length };
  }, [users]);

  const lowCoverage = useMemo(() => {
    const cov = stats?.function_coverage || {};
    return Object.entries(cov)
      .filter(([, rate]) => typeof rate === "number" && rate < 0.4)
      .sort((a, b) => a[1] - b[1])
      .slice(0, 4);
  }, [stats]);

  const disk = health?.data_volume;

  const sessionExtra =
    authEnabled && user ? (
      <Tooltip
        title={`登录账号 ${user.username} · ${ROLE_LABEL[user.role] || user.role}`}
      >
        <Tag color="blue" style={{ margin: 0, cursor: "default", fontSize: BODY }}>
          {user.display_name || user.username}
        </Tag>
      </Tooltip>
    ) : null;

  if (loading || !allowed) return null;

  return (
    <div style={{ maxWidth: 1080 }}>
      <Title level={3} style={{ marginTop: 0, marginBottom: 20 }}>
        {ADMIN_NAV_LABELS.overview}
      </Title>

      <Spin spinning={loadingData}>
        <Section
          title="用户"
          tip="已开通账号的数量与角色分布。右侧为当前登录身份。"
          extra={sessionExtra}
        >
          <Card size="small" styles={CARD_STYLES}>
            {canLoadUsers ? (
              <Row gutter={[24, 20]}>
                <Col xs={12} sm={6}>
                  <Metric
                    title="账号总数"
                    value={userSummary.total}
                    tip="系统中已创建的全部账号（含停用）。"
                  />
                </Col>
                <Col xs={12} sm={6}>
                  <Metric title="报价工程师" value={userSummary.engineers} />
                </Col>
                <Col xs={12} sm={6}>
                  <Metric title="资料库管理员" value={userSummary.admins} />
                </Col>
                <Col xs={12} sm={6}>
                  <Metric
                    title="已停用"
                    value={userSummary.inactive}
                    tip="停用账号无法登录，可在「用户管理」中恢复。"
                    valueStyle={
                      userSummary.inactive > 0 ? { color: "#d48806" } : undefined
                    }
                  />
                </Col>
              </Row>
            ) : (
              <Text type="secondary" style={{ fontSize: BODY }}>
                未启用登录鉴权
              </Text>
            )}
          </Card>
        </Section>

        <Section
          title="知识库"
          tip="历史项目与文档规模，以及各项目能否被 RFQ 相似检索使用。异常请到左侧「知识库」处理。"
        >
          <Card size="small" styles={CARD_STYLES}>
            <Row gutter={[24, 20]}>
              <Col xs={12} sm={6}>
                <Metric
                  title="历史项目"
                  value={stats?.total_projects ?? 0}
                  tip="已纳入知识库的历史项目数量。"
                />
              </Col>
              <Col xs={12} sm={6}>
                <Metric
                  title="文档数"
                  value={stats?.total_documents ?? 0}
                  tip="项目包中的 RFQ、QA、人力报价等文件数量。"
                />
              </Col>
              <Col xs={12} sm={6}>
                <Metric
                  title="知识条目"
                  value={stats?.total_chunks ?? 0}
                  tip="可供「相似历史项目」检索使用的内容条数，越多通常覆盖越全。"
                />
              </Col>
              <Col xs={12} sm={6}>
                <Metric
                  title="最近更新"
                  value={formatTime(stats?.last_import_at)}
                  tip="最近一次把项目资料更新进检索库的时间。"
                  valueStyle={{ fontSize: 18, fontWeight: 600 }}
                />
              </Col>
            </Row>

            <Divider style={{ margin: "16px 0" }} />

            <div style={{ marginBottom: 10 }}>
              <Text strong style={{ fontSize: BODY }}>
                检索可用性
              </Text>
              <Tip title="历史项目资料能否出现在 RFQ「相似历史项目」结果中。红色/黄色项需到「知识库 → 历史项目」补全信息或重新更新。" />
              <Text type="secondary" style={{ fontSize: BODY, marginLeft: 10 }}>
                共 {kbHealth.total} 个
              </Text>
            </div>
            <Space wrap size={[10, 10]}>
              <Tooltip title="资料已就绪，可出现在 RFQ 相似项目结果中。">
                <Tag
                  color="success"
                  style={{ fontSize: BODY, padding: "2px 10px", cursor: "help" }}
                >
                  可检索 {kbHealth.indexed}
                </Tag>
              </Tooltip>
              <Tooltip title="资料已上传，正在等待或排队更新进检索库。">
                <Tag style={{ fontSize: BODY, padding: "2px 10px", cursor: "help" }}>
                  更新中 {kbHealth.pending}
                </Tag>
              </Tooltip>
              <Tooltip title="更新未成功，该项目暂时不会出现在相似检索中。请到知识库查看原因后重试。">
                <Tag
                  color={kbHealth.failed ? "error" : "default"}
                  style={{ fontSize: BODY, padding: "2px 10px", cursor: "help" }}
                >
                  更新失败 {kbHealth.failed}
                </Tag>
              </Tooltip>
              <Tooltip title="缺少客户、年份或工程领域等必填信息，补全后才能用于检索。">
                <Tag
                  color={kbHealth.incomplete ? "warning" : "default"}
                  style={{ fontSize: BODY, padding: "2px 10px", cursor: "help" }}
                >
                  信息待补全 {kbHealth.incomplete}
                </Tag>
              </Tooltip>
            </Space>
            {lowCoverage.length > 0 ? (
              <div style={{ marginTop: 12 }}>
                <Text style={{ fontSize: BODY }}>
                  领域覆盖偏低
                  <Tip title="这些工程领域的历史项目较少，RFQ 对标时可选参考可能偏少。" />
                </Text>
                <div style={{ marginTop: 8 }}>
                  {lowCoverage.map(([fn, rate]) => (
                    <Tag key={fn} color="orange" style={{ fontSize: 13 }}>
                      {fn} {Math.round(rate * 100)}%
                    </Tag>
                  ))}
                </div>
              </div>
            ) : null}
            {stats?.mock_rag ? (
              <Alert
                type="warning"
                showIcon
                style={{ marginTop: 12 }}
                message="当前为演示数据，非生产真实知识库。"
              />
            ) : null}
          </Card>
        </Section>

        <Section title="系统运行" tip="AI 服务可用性与数据盘容量，影响分析与导入是否可正常进行。">
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Card
                size="small"
                styles={{ ...CARD_STYLES, body: { ...CARD_STYLES.body, minHeight: 132 } }}
                title={
                  <span>
                    AI 服务
                    <Tip title="本地大模型与 Embedding 是否可用，影响 RFQ 分析与知识库检索。" />
                  </span>
                }
              >
                <Space direction="vertical" size={10} style={{ width: "100%" }}>
                  <Tag
                    color={aiHealthTagColor(ai.tone)}
                    style={{ fontSize: BODY, padding: "4px 12px", margin: 0 }}
                  >
                    {ai.label}
                  </Tag>
                  <Text style={{ fontSize: BODY, lineHeight: 1.6 }}>{ai.detail}</Text>
                  {health?.version ? (
                    <Text type="secondary" style={{ fontSize: BODY }}>
                      平台版本 {health.version}
                      {health.deploy_sha ? ` · ${health.deploy_sha.slice(0, 7)}` : ""}
                    </Text>
                  ) : null}
                </Space>
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card
                size="small"
                styles={{ ...CARD_STYLES, body: { ...CARD_STYLES.body, minHeight: 132 } }}
                title={
                  <span>
                    数据盘
                    <Tip title="知识库与上传文件所在磁盘。空间不足或写保护会导致上传与更新失败。" />
                  </span>
                }
              >
                {disk ? (
                  <Space direction="vertical" size={10} style={{ width: "100%" }}>
                    <Text strong style={{ fontSize: 20 }}>
                      {formatBytes(disk.used_bytes)} / {formatBytes(disk.total_bytes)}
                    </Text>
                    <Progress
                      percent={Math.min(100, Math.round(disk.usage_percent || 0))}
                      status={
                        disk.write_protected
                          ? "exception"
                          : disk.warning
                            ? "active"
                            : "normal"
                      }
                    />
                    <Space size={10} wrap>
                      {disk.write_protected ? (
                        <Tag color="error" style={{ fontSize: BODY }}>
                          写保护
                        </Tag>
                      ) : disk.warning ? (
                        <Tag color="warning" style={{ fontSize: BODY }}>
                          空间紧张
                        </Tag>
                      ) : (
                        <Tag color="success" style={{ fontSize: BODY }}>
                          空间正常
                        </Tag>
                      )}
                      <Text type="secondary" style={{ fontSize: BODY }}>
                        剩余 {formatBytes(disk.free_bytes)}
                      </Text>
                    </Space>
                  </Space>
                ) : (
                  <Text type="secondary" style={{ fontSize: BODY }}>
                    —
                  </Text>
                )}
              </Card>
            </Col>
          </Row>
        </Section>
      </Spin>
    </div>
  );
}
