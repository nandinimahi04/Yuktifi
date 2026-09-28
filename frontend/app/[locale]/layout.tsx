import type { Metadata, Viewport } from "next";
import { Fraunces, Plus_Jakarta_Sans, Noto_Sans_Devanagari } from "next/font/google";
import "../globals.css";
import { StoreProvider } from "@/lib/store";
import { Sidebar } from "@/components/Sidebar";
import DataModeBanner from "@/components/DataModeBanner";
import NextTopLoader from 'nextjs-toploader';
import dynamic from "next/dynamic";
import Image from "next/image";

// Lazy-load CopilotOverlay: it imports framer-motion + API client.
// We don't need those on the initial page load for every route.
const CopilotOverlay = dynamic(
  () => import("@/components/CopilotOverlay").then((m) => ({ default: m.CopilotOverlay })),
  { ssr: false }
);

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap",
});

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-jakarta",
  display: "swap",
});

const notoSansDevanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari", "latin"],
  weight: ["400", "500", "700", "900"],
  variable: "--font-noto-devanagari",
  display: "swap",
});
export const metadata: Metadata = {
  title: "YuktiFi — Business Planning Platform",
  description: "AI-powered business planning and market intelligence for Indian entrepreneurs.",
  manifest: "/manifest.json",
  icons: {
    icon: "/yukti-logo-transparent.png"
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "YuktiFi",
  },
};

export const viewport: Viewport = {
  themeColor: "#f97316",
  width: "device-width",
  initialScale: 1,
  minimumScale: 1,
};

import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';

export default async function RootLayout({
  children,
  params: { locale }
}: Readonly<{
  children: React.ReactNode;
  params: { locale: string };
}>) {
  // Fetch messages from next-intl configuration
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body suppressHydrationWarning className={`${fraunces.variable} ${jakarta.variable} ${notoSansDevanagari.variable} ${locale === 'hi' ? 'font-devanagari' : 'font-sans'} min-h-screen bg-[#fdfbf6] text-ink antialiased flex flex-col`}>
        <NextTopLoader color="#ea580c" showSpinner={false} shadow="0 0 10px #ea580c,0 0 5px #ea580c" />
        <NextIntlClientProvider messages={messages}>
          <StoreProvider>
            {/* Sits above everything and renders nothing unless the backend
                reports that its data is not live. Without it a demo run and a
                live run are indistinguishable on screen. */}
            <DataModeBanner />
            <div className="flex min-h-screen w-full">
              <Sidebar />

              {/* Main Content Area */}
              <div className="flex-1 flex flex-col min-h-screen w-full">
                {/* Mobile Header (Hidden on Desktop) */}
                <header className="md:hidden bg-white h-14 flex items-center px-4 border-b border-premium-border shadow-sm shrink-0">
                  <Image
                    src="/yukti-logo-transparent.png"
                    alt="YuktiFi Logo"
                    width={32}
                    height={32}
                    className="object-contain mr-2 drop-shadow-sm -mt-0.5"
                    priority
                  />
                  <span className="text-xl font-bold tracking-tight text-[#ea580c]">YuktiFi</span>
                </header>

                <main className="flex-1 w-full bg-[#fdfbf6]">
                  {children}
                </main>
              </div>
              
              <CopilotOverlay />
            </div>
          </StoreProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
