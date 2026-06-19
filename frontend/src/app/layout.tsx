import { AntdRegistry } from "@ant-design/nextjs-registry";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import type { Metadata } from "next";
import AppLayout from "@/components/AppLayout";
import { edagTheme } from "@/theme/edagTheme";

export const metadata: Metadata = {
  title: "ARIA · 智能报价辅助系统",
  description: "EDAG 本地私有化 AI 报价辅助工具",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <AntdRegistry>
          <ConfigProvider theme={edagTheme} locale={zhCN}>
            <AppLayout>{children}</AppLayout>
          </ConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  );
}
