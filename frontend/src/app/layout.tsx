import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/lib/providers";
import { Nav } from "@/components/nav";

export const metadata: Metadata = {
  title: "FinFlow — Transaction Intelligence",
  description:
    "Deterministic multi-agent financial transaction intelligence dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="flex">
            <Nav />
            <main className="flex-1 min-h-screen p-8 max-w-[1400px]">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
