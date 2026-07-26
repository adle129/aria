"use client";

import { Alert } from "antd";
import {
  RFQ_BUSY_HOURS_BANNER_MESSAGE,
  shouldShowBusyHoursBanner,
} from "@/lib/rfqBusyUx";

export default function RfqBusyHoursBanner(props: {
  queuePosition?: number | null;
  estimatedWaitSeconds?: number | null;
}) {
  if (!shouldShowBusyHoursBanner(props)) return null;
  return (
    <Alert
      type="warning"
      showIcon
      banner
      style={{ marginBottom: 12 }}
      message={RFQ_BUSY_HOURS_BANNER_MESSAGE}
      data-testid="rfq-busy-hours-banner"
    />
  );
}
