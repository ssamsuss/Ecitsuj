import type { ReactNode } from "react";
import Link from "next/link";
import "./globals.css";

export const metadata = {
  title: "Mock Jury Dashboard",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="legal-banner">
          Not legal advice. This tool simulates juror deliberation for research and training only.
        </div>
        <header className="site-header">
          <Link href="/">Mock Jury Dashboard</Link>
          {" · "}
          <Link href="/new">New Simulation</Link>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
