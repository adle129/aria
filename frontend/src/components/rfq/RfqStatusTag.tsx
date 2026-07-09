"use client";

import { Tag } from "antd";
import { formatTaskListStatus, getProcessingStatusTagStyle } from "@/lib/taskStatus";

interface RfqStatusTagProps {
  processingStatus: string;
  statusMessage?: string | null;
}

export default function RfqStatusTag({ processingStatus, statusMessage }: RfqStatusTagProps) {
  const style = getProcessingStatusTagStyle(processingStatus);
  return (
    <Tag
      style={{
        color: style.color,
        background: style.background,
        borderColor: style.borderColor,
        margin: 0,
        fontWeight: 500,
      }}
    >
      {formatTaskListStatus({ processing_status: processingStatus, status_message: statusMessage })}
    </Tag>
  );
}
