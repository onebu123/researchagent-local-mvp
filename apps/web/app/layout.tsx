import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ResearchAgent",
  description: "可审计科研论文多 Agent dashboard",
  icons: {
    icon: "/favicon.svg"
  }
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
