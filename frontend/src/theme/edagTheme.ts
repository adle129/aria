import type { ThemeConfig } from "antd";

/** EDAG-inspired theme: white/gray base + signal red accent */
export const edagTheme: ThemeConfig = {
  token: {
    colorPrimary: "#E30613",
    colorLink: "#E30613",
    colorText: "#333333",
    colorTextSecondary: "#666666",
    colorBgLayout: "#F5F5F5",
    colorBgContainer: "#FFFFFF",
    borderRadius: 4,
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
  },
  components: {
    Layout: {
      headerBg: "#FFFFFF",
      siderBg: "#FFFFFF",
      bodyBg: "#F5F5F5",
    },
    Menu: {
      itemSelectedBg: "#FFF1F0",
      itemSelectedColor: "#E30613",
    },
  },
};
