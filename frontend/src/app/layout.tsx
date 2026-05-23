import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FileBRSR — India's ESG Infrastructure Platform | BRSR Compliance + Supply Chain ESG + Carbon Market",
  description:
    "AI-powered BRSR filing in 60 seconds. Supply chain ESG ratings for 100K+ suppliers. Carbon credit facilitation via India's CCTS. Replace ₹15L consultants with one platform.",
  keywords: ["BRSR", "ESG", "SEBI", "sustainability", "supply chain ESG India", "BRSR compliance", "carbon credits India", "BRSR filing software", "ESG assessment platform", "NGRBC principles"],
  openGraph: {
    title: "FileBRSR — India's ESG Infrastructure Platform",
    description: "BRSR filing + Supply Chain ESG + Carbon Market. One platform for SEBI compliance.",
    type: "website",
    url: "https://filebrsr.com",
    siteName: "FileBRSR",
  },
  twitter: {
    card: "summary_large_image",
    title: "FileBRSR — BRSR Compliance + Supply Chain ESG + Carbon Market",
    description: "AI-powered BRSR filing. Supply chain ESG ratings. Carbon credit facilitation. Built for SEBI compliance.",
  },
  alternates: {
    canonical: "https://filebrsr.com",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistMono.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
        <script src="https://accounts.google.com/gsi/client" async />
        <script src="https://checkout.razorpay.com/v1/checkout.js" async />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: "FileBRSR",
              applicationCategory: "BusinessApplication",
              description: "India's ESG infrastructure platform — AI-powered BRSR filing, supply chain ESG ratings, and carbon credit facilitation.",
              url: "https://filebrsr.com",
              offers: [
                { "@type": "Offer", price: "0", priceCurrency: "INR", description: "Free — Supplier self-assessment" },
                { "@type": "Offer", price: "50000", priceCurrency: "INR", description: "Pro — BRSR filing + 50 suppliers" },
              ],
              operatingSystem: "Web",
              featureList: "BRSR Filing, Supply Chain ESG, Carbon Calculator, Benchmarks, XBRL Export, Multi-framework Mapping",
            }),
          }}
        />
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='dark'){document.documentElement.classList.add('dark')}}catch(e){}})()`,
          }}
        />
      </head>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
