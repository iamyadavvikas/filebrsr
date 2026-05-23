"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { Menu, X, ChevronDown, User, CreditCard, LogOut, Moon, Sun } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { useTheme } from "@/components/ThemeProvider";

interface NavUser {
  email: string;
  name?: string;
  plan?: string;
}

export default function Navbar({ user: userProp }: { user?: NavUser | null }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [user, setUser] = useState<NavUser | null>(userProp || null);
  const [authLoaded, setAuthLoaded] = useState(!!userProp);
  const profileRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();

  // Auto-detect auth if no user prop passed
  useEffect(() => {
    if (userProp) {
      setUser(userProp);
      setAuthLoaded(true);
      return;
    }
    const loadUser = async () => {
      const supabase = createClient();
      const { data: { user: authUser } } = await supabase.auth.getUser();
      if (authUser) {
        setUser({
          email: authUser.email ?? "",
          name: authUser.user_metadata?.full_name || authUser.user_metadata?.name || "",
          plan: "Free",
        });
      }
      setAuthLoaded(true);
    };
    loadUser();
  }, [userProp]);

  const navLinks = [
    { href: "/platform", label: "Platform" },
    { href: "/readiness", label: "Free Assessment" },
    { href: "/resources", label: "Resources" },
    { href: "/pricing", label: "Pricing" },
  ];

  const handleSignOut = async () => {
    await fetch("/api/auth/signout", { method: "POST" });
    window.location.href = "/";
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const displayName = user?.name || user?.email?.split("@")[0] || "";
  const initials = displayName.slice(0, 1).toUpperCase();
  const planLabel = user?.plan || "Free";
  const { theme, toggleTheme } = useTheme();

  return (
    <nav className="sticky top-0 z-50 border-b border-border" style={{ background: "var(--nav-bg)", backdropFilter: "blur(16px)" }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-7">
        <div className="flex items-center" style={{ height: 58 }}>
          <Link href="/" className="flex items-center gap-2">
            <Image src="/logo.svg" alt="fileBRSR" width={160} height={40} priority />
          </Link>

          {/* Desktop nav - left aligned after logo */}
          <div className="hidden md:flex items-center gap-7 ml-8">
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
          </div>

          {/* Right side: theme toggle + profile */}
          <div className="hidden md:flex items-center gap-4 ml-auto">

            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className="w-8 h-8 flex items-center justify-center rounded-lg border border-border text-muted hover:text-foreground hover:bg-card transition-colors"
              aria-label="Toggle theme"
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            {/* Profile dropdown */}
            {user ? (
              <div className="relative" ref={profileRef}>
                <button
                  onClick={() => setProfileOpen(!profileOpen)}
                  className="flex items-center gap-2 text-sm font-medium text-foreground hover:text-primary transition-colors"
                >
                  <div
                    className="flex items-center justify-center text-white font-bold"
                    style={{ width: 30, height: 30, borderRadius: "50%", background: "#1B4D3E", fontSize: 12 }}
                  >
                    {initials}
                  </div>
                  <span className="max-w-[120px] truncate">{displayName}</span>
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${profileOpen ? "rotate-180" : ""}`} />
                </button>

                {profileOpen && (
                  <div
                    className="absolute right-0 mt-2 bg-card border border-border shadow-lg"
                    style={{ borderRadius: 12, width: 240, padding: "8px 0", zIndex: 100 }}
                  >
                    {/* User info */}
                    <div className="border-b border-border" style={{ padding: "12px 16px" }}>
                      <p className="text-foreground" style={{ fontSize: 13, fontWeight: 600 }}>{displayName}</p>
                      <p className="text-muted" style={{ fontSize: 12, marginTop: 2 }}>{user.email}</p>
                    </div>

                    {/* Plan */}
                    <div className="border-b border-border" style={{ padding: "10px 16px" }}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <CreditCard className="w-3.5 h-3.5 text-muted" />
                          <span style={{ fontSize: 12, color: "var(--muted)" }}>Plan</span>
                        </div>
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 600,
                            padding: "2px 8px",
                            borderRadius: 6,
                            background: planLabel === "Free" ? "var(--surface)" : "var(--icon-soft)",
                            color: planLabel === "Free" ? "var(--muted)" : "var(--success)",
                          }}
                        >
                          {planLabel}
                        </span>
                      </div>
                    </div>

                    {/* Links */}
                    <div style={{ padding: "4px 0" }}>
                      <Link
                        href="/platform"
                        onClick={() => setProfileOpen(false)}
                        className="flex items-center gap-2 px-4 py-2 text-sm text-foreground hover:bg-gray-50 transition-colors"
                      >
                        <User className="w-3.5 h-3.5 text-muted" />
                        Platform
                      </Link>
                      <Link
                        href="/pricing"
                        onClick={() => setProfileOpen(false)}
                        className="flex items-center gap-2 px-4 py-2 text-sm text-foreground hover:bg-gray-50 transition-colors"
                      >
                        <CreditCard className="w-3.5 h-3.5 text-muted" />
                        Upgrade Plan
                      </Link>
                    </div>

                    {/* Sign out */}
                    <div style={{ borderTop: "1px solid var(--border)", padding: "4px 0" }}>
                      <button
                        onClick={handleSignOut}
                        className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                      >
                        <LogOut className="w-3.5 h-3.5" />
                        Sign Out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : authLoaded ? (
              <Link
                href="/login"
                className="text-white text-sm font-semibold"
                style={{ padding: "8px 20px", borderRadius: 10, background: "#1B4D3E" }}
              >
                Log In
              </Link>
            ) : null}
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
              <>
                <div className="py-2 border-t border-border mt-2 pt-3">
                  <p className="text-xs text-muted px-1">Signed in as</p>
                  <p className="text-sm font-medium mt-0.5 px-1">{displayName}</p>
                  <p className="text-xs text-muted px-1">{user.email}</p>
                  <div className="flex items-center gap-2 mt-2 px-1">
                    <span className="text-xs text-muted">Plan:</span>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        padding: "2px 8px",
                        borderRadius: 6,
                        background: planLabel === "Free" ? "#F3F4F6" : "#F0FDF4",
                        color: planLabel === "Free" ? "#6B7280" : "#166534",
                      }}
                    >
                      {planLabel}
                    </span>
                  </div>
                </div>
                <button
                  onClick={handleSignOut}
                  className="block w-full text-left py-2 mt-2 text-sm font-medium text-red-600 hover:text-red-700"
                >
                  Sign Out
                </button>
              </>
            ) : authLoaded ? (
              <Link
                href="/login"
                className="block mt-2 px-4 py-2 bg-primary text-white text-sm font-semibold text-center"
                style={{ borderRadius: 10, background: "#1B4D3E" }}
                onClick={() => setMobileOpen(false)}
              >
                Log In
              </Link>
            ) : null}
          </div>
        )}
      </div>
    </nav>
  );
}
