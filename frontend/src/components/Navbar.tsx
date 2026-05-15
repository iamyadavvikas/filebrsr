"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X } from "lucide-react";

export default function Navbar({ user }: { user?: { email: string } | null }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  const navLinks = user
    ? [
        { href: "/dashboard", label: "Dashboard" },
        { href: "/upload", label: "Extract" },
        { href: "/pricing", label: "Pricing" },
      ]
    : [
        { href: "/upload", label: "Extract" },
        { href: "/pricing", label: "Pricing" },
      ];

  const handleSignOut = async () => {
    await fetch("/api/auth/signout", { method: "POST" });
    window.location.href = "/";
  };

  return (
    <nav className="sticky top-0 z-50 border-b border-border" style={{ background: "rgba(250,251,249,0.92)", backdropFilter: "blur(16px)" }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-7">
        <div className="flex justify-between items-center" style={{ height: 58 }}>
          <Link href="/" className="flex items-center gap-2">
            <Image src="/logo.svg" alt="fileBRSR" width={160} height={40} priority />
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-7">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm font-medium transition-colors hover:text-primary ${
                  pathname === link.href ? "text-primary" : "text-muted"
                }`}
              >
                {link.label}
              </Link>
            ))}
            {user ? (
              <div className="flex items-center gap-4">
                <span className="text-sm text-muted">{user.email}</span>
                <button
                  onClick={handleSignOut}
                  className="text-sm font-medium text-muted hover:text-foreground transition-colors"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Link
                  href="/login"
                  className="text-sm font-medium text-muted hover:text-foreground transition-colors"
                >
                  Log In
                </Link>
                <Link
                  href="/signup"
                  className="text-white text-sm font-semibold transition-colors"
                  style={{ padding: "8px 22px", borderRadius: 10, background: "#1B4D3E" }}
                >
                  Try Free →
                </Link>
              </div>
            )}
          </div>

          {/* Mobile toggle */}
          <button
            className="md:hidden p-2"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile menu */}
        {mobileOpen && (
          <div className="md:hidden pb-4 border-t border-border pt-4">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="block py-2 text-sm font-medium text-muted hover:text-primary"
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </Link>
            ))}
            {user ? (
              <button
                onClick={handleSignOut}
                className="block w-full text-left py-2 text-sm font-medium text-muted hover:text-foreground"
              >
                Sign Out
              </button>
            ) : (
              <>
                <Link
                  href="/login"
                  className="block py-2 text-sm font-medium text-muted hover:text-primary"
                  onClick={() => setMobileOpen(false)}
                >
                  Log In
                </Link>
                <Link
                  href="/signup"
                  className="block mt-2 px-4 py-2 bg-primary text-white text-sm font-semibold text-center"
                  style={{ borderRadius: 10 }}
                  onClick={() => setMobileOpen(false)}
                >
                  Try Free →
                </Link>
              </>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}
