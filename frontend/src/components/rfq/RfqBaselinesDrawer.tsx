"use client";

import { Drawer } from "antd";
import ManpowerBaselinesPanel from "@/components/ManpowerBaselinesPanel";

type Props = {
  open: boolean;
  engagementId: string | null;
  onClose: () => void;
};

/** RFQ-page baselines detail (R1-CHG01); avoids navigating to /knowledge. */
export default function RfqBaselinesDrawer({ open, engagementId, onClose }: Props) {
  return (
    <Drawer
      title="历史项目人天明细"
      placement="right"
      width={720}
      open={open}
      onClose={onClose}
      destroyOnClose
    >
      {engagementId ? (
        <ManpowerBaselinesPanel engagementId={engagementId} />
      ) : (
        <span>未找到该历史项目的人天明细。</span>
      )}
    </Drawer>
  );
}
