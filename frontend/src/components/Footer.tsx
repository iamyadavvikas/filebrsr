import Link from "next/link";
import Image from "next/image";

export default function Footer() {
  return (
    <footer className="border-t border-border" style={{ padding: "40px 28px", textAlign: "center" }}>
      <div className="flex items-center justify-center gap-2 mb-2.5">
        <Image src="/logo-icon.svg" alt="FileBRSR" width={26} height={26} />
        <span className="font-extrabold text-primary" style={{ fontSize: 17 }}>
          file<span className="text-accent">BRSR</span>
        </span>
      </div>
      <p className="text-muted-light" style={{ fontSize: 12 }}>
        AI-powered BRSR compliance for India&apos;s listed companies
      </p>
      <p style={{ fontSize: 11, color: "#D1D5DB", marginTop: 6 }}>
        © {new Date().getFullYear()} FileBRSR · Made in India 🇮🇳 ·{" "}
        <Link href="mailto:support@filebrsr.com" style={{ color: "#9CA3AF" }}>
          support@filebrsr.com
        </Link>
      </p>
    </footer>
  );
}
