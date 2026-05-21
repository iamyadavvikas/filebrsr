"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ProcessingPoller() {
  const router = useRouter();

  useEffect(() => {
    const interval = setInterval(() => {
      router.refresh();
    }, 5000);

    return () => clearInterval(interval);
  }, [router]);

  return (
    <p className="text-xs text-muted mt-3 animate-pulse">
      Auto-refreshing every 5 seconds...
    </p>
  );
}
