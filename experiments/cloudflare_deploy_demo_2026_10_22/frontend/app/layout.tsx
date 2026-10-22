import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cloudflare deploy demo",
  description: "Next.js page that calls a FastAPI Worker on Cloudflare.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
