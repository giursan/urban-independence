import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import { RegisterSW } from "@/components/RegisterSW";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Companion",
  description: "A warm AI companion to talk, reflect, and stay connected.",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, title: "Companion", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  themeColor: "#1d4ed8",
  width: "device-width",
  initialScale: 1,
};

// Apply the saved font-size before paint to avoid a flash.
const fontScaleInit = `(function(){try{var s=localStorage.getItem('font-scale');if(s){document.documentElement.style.setProperty('--font-scale',s);}}catch(e){}})();`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} h-full`}>
      <body className="min-h-full flex flex-col antialiased">
        <script dangerouslySetInnerHTML={{ __html: fontScaleInit }} />
        {children}
        <RegisterSW />
      </body>
    </html>
  );
}
