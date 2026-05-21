import Link from "next/link";
import Image from "next/image";

export default function Footer() {
  return (
    <footer className="border-t border-border" style={{ background: "var(--surface)" }}>
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
          {/* Brand */}
          <div className="md:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <Image src="/logo-icon.svg" alt="FileBRSR" width={28} height={28} />
              <span className="font-extrabold" style={{ fontSize: 18, color: "var(--primary)" }}>
                file<span style={{ color: "var(--accent)" }}>BRSR</span>
              </span>
            </div>
            <p style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.7 }}>
              #1 AI-powered BRSR compliance platform for Indian listed companies.
            </p>
          </div>

          {/* Platform */}
          <div>
            <h4 style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, textTransform: "uppercase", color: "var(--primary)", marginBottom: 14 }}>Platform</h4>
            <ul className="space-y-2.5">
              {[
                { label: "Upload & Extract", href: "/upload" },
                { label: "Pricing", href: "/pricing" },
                { label: "Dashboard", href: "/dashboard" },
              ].map((l) => (
                <li key={l.label}>
                  <Link href={l.href} className="text-sm text-muted hover:text-foreground transition-colors">{l.label}</Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, textTransform: "uppercase", color: "var(--primary)", marginBottom: 14 }}>Resources</h4>
            <ul className="space-y-2.5">
              {[
                { label: "BRSR Framework Guide", href: "https://www.sebi.gov.in/legal/regulations/may-2021/business-responsibility-and-sustainability-reporting-by-listed-entities_50096.html" },
                { label: "NGRBC Principles", href: "https://www.mca.gov.in/Ministry/pdf/NationalGuildeline_15032019.pdf" },
                { label: "SEBI Circulars", href: "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=2&smid=0" },
              ].map((l) => (
                <li key={l.label}>
                  <Link href={l.href} target="_blank" rel="noopener noreferrer" className="text-sm text-muted hover:text-foreground transition-colors">{l.label}</Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, textTransform: "uppercase", color: "var(--primary)", marginBottom: 14 }}>Legal</h4>
            <ul className="space-y-2.5">
              {[
                { label: "Terms of Use", href: "#" },
                { label: "Privacy Policy", href: "#" },
                { label: "Contact", href: "mailto:support@filebrsr.com" },
              ].map((l) => (
                <li key={l.label}>
                  <Link href={l.href} className="text-sm text-muted hover:text-foreground transition-colors">{l.label}</Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-10 pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-3">
          <p style={{ fontSize: 12, color: "var(--muted-light)" }}>
            © {new Date().getFullYear()} FileBRSR. All rights reserved. Made in India 🇮🇳
          </p>
          <Link href="mailto:support@filebrsr.com" className="text-xs text-muted hover:text-foreground transition-colors">
            support@filebrsr.com
          </Link>
        </div>
      </div>
    </footer>
  );
}
