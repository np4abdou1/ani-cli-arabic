import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AniCliAr Command Center — Analytics & Operations",
  description: "Real-time edge telemetry, stream analytics, and remote broadcast management for ani-cli-arabic.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-slate-100 min-h-screen antialiased selection:bg-primary selection:text-slate-900">
        {children}
      </body>
    </html>
  );
}
