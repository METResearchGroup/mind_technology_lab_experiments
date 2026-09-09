import type { Metadata } from "next";
import { Figtree, Instrument_Serif } from "next/font/google";
import "./globals.css";

const instrument = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-instrument",
});

const figtree = Figtree({
  subsets: ["latin"],
  variable: "--font-figtree",
});

export const metadata: Metadata = {
  title: "LifeMem — identity essentialism in LLM agents",
  description:
    "Replication dashboard for LifeMem (arXiv:2608.19621): longitudinal memory for LLM social agents.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${instrument.variable} ${figtree.variable} antialiased`}>
        <div className="grain" aria-hidden="true" />
        {children}
      </body>
    </html>
  );
}
