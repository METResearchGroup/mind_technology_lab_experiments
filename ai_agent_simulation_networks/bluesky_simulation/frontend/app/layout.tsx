import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bluesky AI Agent Simulation",
  description: "Social Science Research Platform for AI Agent Behavior Simulation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
