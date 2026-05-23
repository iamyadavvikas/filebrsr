"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
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
} from "lucide-react";

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
  const [collapsed, setCollapsed] = useState(false);
  const [userId, setUserId] = useState<string | undefined>();

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      if (data.user) setUserId(data.user.id);
    });
  }, []);

  return (
    <AnalyticsProvider userId={userId}>
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside
        className={`${
          collapsed ? "w-16" : "w-64"
        } text-white flex flex-col transition-all duration-300 ease-in-out`}
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
          {navGroups.map((group, gi) => (
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
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
    </AnalyticsProvider>
  );
}
