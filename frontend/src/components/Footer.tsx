import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-border" style={{ padding: "40px 28px", textAlign: "center" }}>
      <div className="flex items-center justify-center gap-2 mb-2.5">
        <div
          className="flex items-center justify-center text-white font-extrabold"
          style={{
            width: 28,
            height: 28,
            borderRadius: 8,
            background: "linear-gradient(135deg, #1B4D3E, #2D7A5F)",
            fontSize: 12,
          }}
        >
          F
        </div>
        <span className="font-extrabold text-primary" style={{ fontSize: 17 }}>
          File<span className="text-accent">BRSR</span>
        </span>
      </div>
      <p className="text-muted-light" style={{ fontSize: 12 }}>
        AI-powered BRSR compliance for India&apos;s listed companies
      </p>
      <p style={{ fontSize: 11, color: "#D1D5DB", marginTop: 6 }}>
        © {new Date().getFullYear()} FileBRSR · Made in India 🇮🇳 ·{" "}
        <Link href="mailto:hello@filebrsr.com" style={{ color: "#9CA3AF" }}>
          hello@filebrsr.com
        </Link>
      </p>
    </footer>
  );
}
