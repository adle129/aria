"use client";

import { MenuOutlined, PlusOutlined, UploadOutlined } from "@ant-design/icons";
import { Button, Drawer, Grid, Typography } from "antd";
import { useState } from "react";
import RfqRecentTasksTable from "@/components/rfq/RfqRecentTasksTable";
import type { TaskSummary } from "@/types/task";

const { useBreakpoint } = Grid;
const { Text } = Typography;

interface RfqRecentTasksSidebarProps {
  tasks: TaskSummary[];
  activeTaskId?: string;
  loading?: boolean;
  uploadDisabled?: boolean;
  onOpen: (taskId: string) => void;
  onUploadNew: () => void;
}

function RecentTasksPanel({
  tasks,
  activeTaskId,
  loading,
  uploadDisabled,
  onOpen,
  onUploadNew,
}: RfqRecentTasksSidebarProps) {
  return (
    <div
      style={{
        background: "#FFFFFF",
        border: "1px solid #EEEEEE",
        borderRadius: 6,
        overflow: "hidden",
        maxHeight: "calc(100vh - 200px)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ padding: "12px 12px 10px", borderBottom: "1px solid #F0F0F0" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 10,
          }}
        >
          <Text strong style={{ fontSize: 13, letterSpacing: 0.2 }}>
            最近 RFQ
          </Text>
          {tasks.length > 0 && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {tasks.length} 份
            </Text>
          )}
        </div>
        <Button
          type="primary"
          block
          icon={<UploadOutlined />}
          disabled={uploadDisabled}
          onClick={onUploadNew}
        >
          上传新 RFQ
        </Button>
      </div>
      <div style={{ overflowY: "auto", flex: 1, minHeight: 120 }}>
        <RfqRecentTasksTable
          tasks={tasks}
          activeTaskId={activeTaskId}
          loading={loading}
          onOpen={onOpen}
        />
      </div>
    </div>
  );
}

export default function RfqRecentTasksSidebar(props: RfqRecentTasksSidebarProps) {
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const [drawerOpen, setDrawerOpen] = useState(false);

  if (isMobile) {
    return (
      <>
        <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            disabled={props.uploadDisabled}
            onClick={props.onUploadNew}
          >
            上传新 RFQ
          </Button>
          {props.tasks.length > 0 && (
            <Button icon={<MenuOutlined />} onClick={() => setDrawerOpen(true)}>
              历史 ({props.tasks.length})
            </Button>
          )}
        </div>
        <Drawer
          title={`最近 RFQ（${props.tasks.length}）`}
          placement="left"
          width={300}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
        >
          <Button
            type="primary"
            block
            icon={<UploadOutlined />}
            disabled={props.uploadDisabled}
            style={{ marginBottom: 12 }}
            onClick={() => {
              setDrawerOpen(false);
              props.onUploadNew();
            }}
          >
            上传新 RFQ
          </Button>
          <RfqRecentTasksTable
            tasks={props.tasks}
            activeTaskId={props.activeTaskId}
            loading={props.loading}
            onOpen={(id) => {
              props.onOpen(id);
              setDrawerOpen(false);
            }}
          />
        </Drawer>
      </>
    );
  }

  return (
    <div style={{ width: 280, flexShrink: 0 }}>
      <RecentTasksPanel {...props} />
    </div>
  );
}
