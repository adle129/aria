"use client";

import { Alert } from "antd";
import type { DiskVolumeHealth } from "@/api/client";
import { capacityAlert } from "@/lib/kbCapacity";

interface KbCapacityAlertProps {
  volume?: DiskVolumeHealth | null;
}

export default function KbCapacityAlert({
  volume,
}: KbCapacityAlertProps) {
  const alert = capacityAlert(volume);
  if (!alert) return null;

  return (
    <Alert
      type={alert.type}
      showIcon
      message={alert.message}
      description={alert.description}
      style={{ marginBottom: 16 }}
    />
  );
}
