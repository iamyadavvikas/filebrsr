"use client";

import { createContext, useContext, useEffect, useCallback, useRef } from "react";
import { usePathname } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

// Analytics context for tracking events throughout the app
interface AnalyticsContextType {
  track: (eventName: string, category: EventCategory, properties?: Record<string, any>) => void;
}

type EventCategory = "auth" | "extraction" | "data_entry" | "report" | "billing" | "navigation" | "team" | "export";

const AnalyticsContext = createContext<AnalyticsContextType>({
  track: () => {},
});

export function useAnalytics() {
  return useContext(AnalyticsContext);
}

// Generate a session ID that persists per browser tab
function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let sid = sessionStorage.getItem("fb_session_id");
  if (!sid) {
    sid = crypto.randomUUID();
    sessionStorage.setItem("fb_session_id", sid);
  }
  return sid;
}

export function AnalyticsProvider({ children, userId }: { children: React.ReactNode; userId?: string }) {
  const pathname = usePathname();
  const lastPathRef = useRef<string | null>(null);

  const track = useCallback(
    (eventName: string, category: EventCategory, properties?: Record<string, any>) => {
      // Fire and forget — don't block UI
      const supabase = createClient();
      supabase
        .from("analytics_events")
        .insert({
          user_id: userId || null,
          event_name: eventName,
          event_category: category,
          properties: properties || {},
          session_id: getSessionId(),
          page_path: typeof window !== "undefined" ? window.location.pathname : null,
          referrer: typeof document !== "undefined" ? document.referrer || null : null,
          user_agent: typeof navigator !== "undefined" ? navigator.userAgent : null,
        })
        .then(() => {}); // silent fire-and-forget
    },
    [userId]
  );

  // Auto-track page views
  useEffect(() => {
    if (pathname && pathname !== lastPathRef.current) {
      lastPathRef.current = pathname;
      track("page_view", "navigation", { path: pathname });
    }
  }, [pathname, track]);

  return (
    <AnalyticsContext value={{ track }}>
      {children}
    </AnalyticsContext>
  );
}
