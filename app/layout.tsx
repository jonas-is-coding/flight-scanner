import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Flight Deal Radar",
  description: "Günstige Wochenendflüge ab NRW, gefunden mit der Amadeus Flight Offers Search API.",
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  );
}
