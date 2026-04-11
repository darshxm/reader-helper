import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PDF Reader Helper",
  description: "AI-powered PDF reader with Gemini",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
