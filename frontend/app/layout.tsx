import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { TRPCProvider } from "@/components/providers/trpc-provider";
import { Toaster } from "@/components/ui/toaster";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReelAgent | AI-Powered Real Estate Content",
  description:
    "Create stunning property content in minutes with AI. Made for real estate agents who want to stand out on social media.",
  keywords: [
    "real estate marketing",
    "property content",
    "AI content creation",
    "Instagram",
    "real estate agent tools",
  ],
  authors: [{ name: "ReelAgent" }],
  openGraph: {
    title: "ReelAgent | AI-Powered Real Estate Content",
    description:
      "Transform property photos into scroll-stopping social content in minutes.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-background font-sans antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          <TRPCProvider>
            {children}
            <Toaster />
          </TRPCProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

