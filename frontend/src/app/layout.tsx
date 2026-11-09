import type { Metadata } from "next";
import "./globals.css";
import { AnalysisProvider } from "@/lib/store";

export const metadata: Metadata = {
  title: "CodeReviewX — Explainable AI Code Health Reviewer",
  description:
    "CodeReviewX combines structural code analysis with Explainable AI to reveal why your code is difficult to maintain.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased dark">
      <body className="min-h-full flex flex-col bg-[#05070d] text-slate-100">
        <AnalysisProvider>{children}</AnalysisProvider>
      </body>
    </html>
  );
}
