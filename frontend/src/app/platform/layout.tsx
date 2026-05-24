"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { AnalyticsProvider } from "@/lib/analytics";
import { createClient } from "@/lib/supabase/client";
import {
  LayoutDashboard,
  FileInput,
  Calculator,
  Target,
  Calendar,
  FileText,
  TrendingUp,
  BarChart3,
  Activity,
  Upload,
  Settings,
  ChevronLeft,
  ChevronRight,
  Network,
  FolderOpen,
  CheckSquare,
  Layers,
  Code,
  Shield,
  ShieldCheck,
  Star,
  Compass,
  ClipboardList,
  MessageSquare,
  PieChart,
  Menu,
  X,
  LogIn,
} from "lucide-react";

const FOUNDER_EMAILS = [
  "ydvikasiitkgp@gmail.com",
  "ydvikas.iitkgp@gmail.com",
  "vkyadav.iitkgp@gmail.com",
  "vikaskashi896@gmail.com",
  "yvikas.free@gmail.com",
];

// Pages accessible without login (guest trial)
const GUEST_ALLOWED_PATHS = ["/platform/data-entry", "/platform/carbon"];

// Grouped by ESG compliance workflow priority
const navGroups = [
  {
    label: "Core Workflow",
    items: [
      { name: "Overview", href: "/platform", icon: LayoutDashboard },
      { name: "Upload & Extract", href: "/platform/upload-extract", icon: Upload },
      { name: "Extraction Results", href: "/platform/reports", icon: ClipboardList },
      { name: "Data Entry", href: "/platform/data-entry", icon: FileInput },
      { name: "Action Plan", href: "/platform/action-plan", icon: Target },
    ],
  },
  {
    label: "Analysis",
    items: [
      { name: "Carbon Calculator", href: "/platform/carbon", icon: Calculator },
      { name: "Materiality", href: "/platform/materiality", icon: Compass },
      { name: "Benchmarks", href: "/platform/benchmarks", icon: BarChart3 },
    ],
  },
  {
    label: "Supply Chain & Compliance",
    items: [
      { name: "Supply Chain ESG", href: "/platform/supply-chain", icon: Network },
      { name: "Documents & Evidence", href: "/platform/documents", icon: FolderOpen },
      { name: "Compliance Tracker", href: "/platform/compliance", icon: Shield },
    ],
  },
  {
    label: "Reporting & Filing",
    items: [
      { name: "Board Dashboard", href: "/platform/board", icon: PieChart },
      { name: "XBRL Filing", href: "/platform/xbrl", icon: Code },
      { name: "Frameworks", href: "/platform/frameworks", icon: Layers },
      { name: "ESG Ratings", href: "/platform/esg-ratings", icon: Star },
    ],
  },
  {
    label: "Monitor",
    items: [
      { name: "Audit Trail", href: "/platform/audit", icon: ShieldCheck },
      { name: "Tracking", href: "/platform/tracking", icon: TrendingUp },
      { name: "Calendar", href: "/platform/calendar", icon: Calendar },
      { name: "Workflows", href: "/platform/workflows", icon: CheckSquare },
      { name: "Surveys", href: "/platform/surveys", icon: MessageSquare },
    ],
  },
  {
    label: "",
    items: [
      { name: "Analytics", href: "/platform/analytics", icon: Activity },
      { name: "Settings", href: "/platform/settings", icon: Settings },
    ],
  },
];

export default function PlatformLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userId, setUserId] = useState<string | undefined>();
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [isFounder, setIsFounder] = useState(false);
  const [isGuest, setIsGuest] = useState(true); // default guest until auth resolves
  const [guestExpired, setGuestExpired] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      if (data.user) {
        setUserId(data.user.id);
        setUserEmail(data.user.email || null);
        setIsGuest(false);
        const founder = FOUNDER_EMAILS.includes(data.user.email || "");
        setIsFounder(founder);
        // Check admin status
        supabase.from("profiles").select("is_admin").eq("id", data.user.id).single().then(({ data: profile }) => {
          if (profile?.is_admin) setIsAdmin(true);
        });
      } else {
        setIsGuest(true);
      }
    });
  }, []);

  // 5-minute guest trial timer
  useEffect(() => {
    if (!isGuest) return;
    const GUEST_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes
    const timer = setTimeout(() => {
      setGuestExpired(true);
    }, GUEST_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [isGuest]);

  // Route guard: non-founder logged-in users can only access data-entry & carbon
  useEffect(() => {
    if (isGuest || isFounder || !pathname) return;
    const isAllowed = GUEST_ALLOWED_PATHS.some((p) => pathname.startsWith(p)) || pathname === "/platform";
    if (!isAllowed) {
      router.replace("/platform/data-entry");
    }
  }, [pathname, isGuest, isFounder, router]);

  // Close mobile sidebar on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // Find current page name for mobile header
  const currentPage = navGroups
    .flatMap((g) => g.items)
    .find((item) => pathname === item.href || (item.href !== "/platform" && pathname?.startsWith(item.href)));

  // Filter nav items: restrict access based on role
  const filteredNavGroups = navGroups.map(group => ({
    ...group,
    items: group.items.filter(item => {
      if (item.href === "/platform/analytics" && !isAdmin) return false;
      // Guests and non-founder users only see data-entry & carbon
      if (!isFounder && !isAdmin) {
        return GUEST_ALLOWED_PATHS.some((p) => item.href.startsWith(p));
      }
      return true;
    }),
  })).filter(group => group.items.length > 0);

  return (
    <AnalyticsProvider userId={userId}>
    <div className="flex h-screen bg-gray-50">

      {/* Guest Trial Expired Modal */}
      {guestExpired && isGuest && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full p-8 text-center">
            <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <LogIn className="w-7 h-7 text-emerald-600" />
            </div>
            <h2 className="text-lg font-bold text-gray-900 mb-2">Free Trial Ended</h2>
            <p className="text-sm text-gray-500 mb-6">
              Your 5-minute free trial has ended. Sign up to continue using Data Entry and Carbon Calculator — it&apos;s free!
            </p>
            <Link
              href="/signup"
              className="block w-full px-5 py-2.5 bg-emerald-600 text-white rounded-lg font-medium text-sm hover:bg-emerald-700 transition-colors mb-3"
            >
              Sign Up Free
            </Link>
            <Link
              href="/login"
              className="block w-full px-5 py-2.5 border border-gray-200 text-gray-700 rounded-lg font-medium text-sm hover:bg-gray-50 transition-colors"
            >
              Already have an account? Log In
            </Link>
          </div>
        </div>
      )}

      {/* Mobile Header Bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 flex items-center h-14 px-3 border-b border-border" style={{ background: "var(--nav-bg)", backdropFilter: "blur(16px)" }}>
        <button
          onClick={() => setMobileOpen(true)}
          className="w-10 h-10 flex items-center justify-center rounded-lg text-foreground"
          aria-label="Open menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex-1 flex items-center justify-center">
          <span className="text-sm font-semibold text-foreground truncate">{currentPage?.name || "Platform"}</span>
        </div>
        <Link href="/platform" className="w-10 h-10 flex items-center justify-center">
          <Image src="/logo-icon.svg" alt="FileBRSR" width={24} height={24} />
        </Link>
      </div>

      {/* Mobile Sidebar Overlay */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMobileOpen(false)}
          />
          {/* Sidebar panel */}
          <aside
            className="absolute left-0 top-0 bottom-0 w-72 text-white flex flex-col overflow-y-auto"
            style={{ background: "linear-gradient(180deg, #0B2B22 0%, #0F3D2E 40%, #1B4D3E 100%)", animation: "slideRight 0.2s ease-out" }}
          >
            {/* Header with close button */}
            <div className="p-4 flex items-center justify-between border-b border-white/10">
              <Image src="/logo.svg" alt="FileBRSR" width={140} height={36} />
              <button
                onClick={() => setMobileOpen(false)}
                className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-3 overflow-y-auto">
              {filteredNavGroups.map((group, gi) => (
                <div key={gi} className={gi > 0 ? "mt-2 pt-2 border-t border-white/10" : ""}>
                  {group.label && (
                    <span className="px-4 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">
                      {group.label}
                    </span>
                  )}
                  {group.items.map((item) => {
                    const isActive =
                      pathname === item.href ||
                      (item.href !== "/platform" && pathname?.startsWith(item.href));
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={() => setMobileOpen(false)}
                        className={`flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg transition-colors ${
                          isActive
                            ? "bg-emerald-600/30 text-emerald-300"
                            : "text-gray-300 hover:bg-white/5 hover:text-white"
                        }`}
                      >
                        <item.icon className="w-4 h-4 flex-shrink-0" />
                        <span className="text-sm">{item.name}</span>
                      </Link>
                    );
                  })}
                </div>
              ))}
            </nav>
          </aside>
        </div>
      )}

      {/* Desktop Sidebar */}
      <aside
        className={`hidden md:flex ${
          collapsed ? "w-16" : "w-64"
        } text-white flex-col transition-all duration-300 ease-in-out`}
        style={{ background: "linear-gradient(180deg, #0B2B22 0%, #0F3D2E 40%, #1B4D3E 100%)" }}
      >
        {/* Logo - links back to home */}
        <Link href="/" className="p-4 flex items-center border-b border-white/10 hover:bg-white/5 transition-colors">
          {collapsed ? (
            <Image src="/logo-icon.svg" alt="FileBRSR" width={32} height={32} />
          ) : (
            <Image src="/logo.svg" alt="FileBRSR" width={160} height={40} />
          )}
        </Link>

        {/* Navigation */}
        <nav className="flex-1 py-2 overflow-y-auto">
          {filteredNavGroups.map((group, gi) => (
            <div key={gi} className={gi > 0 ? "mt-3 pt-3 border-t border-white/10" : ""}>
              {!collapsed && group.label && (
                <span className="px-4 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">
                  {group.label}
                </span>
              )}
              {group.items.map((item) => {
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/platform" && pathname?.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 px-4 py-2 mx-2 rounded-lg transition-colors ${
                      isActive
                        ? "bg-emerald-600/30 text-emerald-300"
                        : "text-gray-300 hover:bg-white/5 hover:text-white"
                    }`}
                    title={collapsed ? item.name : undefined}
                  >
                    <item.icon className="w-4 h-4 flex-shrink-0" />
                    {!collapsed && (
                      <span className="text-sm">{item.name}</span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Collapse button */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-3 border-t border-white/10 hover:bg-white/5 transition-colors flex items-center justify-center"
        >
          {collapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <ChevronLeft className="w-5 h-5" />
          )}
        </button>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto pt-14 md:pt-0">
        {children}
      </main>
    </div>
    </AnalyticsProvider>
  );
}
