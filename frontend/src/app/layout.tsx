import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Recruiter Ranking Engine",
  description: "Multi-signal ML-ranked candidate shortlisting",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <header className="border-b border-neutral-200 bg-white">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <div>
              <h1 className="font-display text-xl font-semibold tracking-tight">
                AI Recruiter Ranking Engine
              </h1>
              <p className="text-xs text-neutral-500">Rank, don&apos;t filter</p>
            </div>
            <span className="badge bg-amber-100 text-amber-800">
              Behavioral data: simulated
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
