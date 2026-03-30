import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import AppShell from "./AppShell";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "GigLeads AI — AI-Powered Client Acquisition",
  description: "Multi-agent system for automated freelance lead generation and proposals",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} antialiased`}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
