import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SELORA — Sensor-aware Lunar Image Registration",
  description:
    "SELORA aligns Chandrayaan-2 lunar imagery across OHRC, TMC-2, and IIRS sensors with sensor-aware, multi-scale registration and quantitative confidence metrics.",
  keywords: [
    "SELORA", "lunar image registration", "Chandrayaan-2", "OHRC", "TMC-2", "IIRS",
    "remote sensing", "computer vision", "image alignment", "ISRO"
  ],
  openGraph: {
    title: "SELORA — Sensor-aware Lunar Image Registration",
    description: "Aligning the Moon across sensors, scales and illumination conditions.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" data-scroll-behavior="smooth">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
