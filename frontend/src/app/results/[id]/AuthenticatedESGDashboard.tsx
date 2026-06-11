"use client";

import { useEffect, useState } from "react";
import { ESGDashboard } from "./ESGDashboard";

interface Props {
  reportData: Record<string, unknown>;
  reportId?: string;
}

export default function AuthenticatedESGDashboard({ reportData, reportId }: Props) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Format data for ESGDashboard which expects BackendResponse shape
    const { gap_analysis, datapoints_stats, benchmark, ...sections } = reportData;
    const formatted = {
      extracted_data: sections,
      gap_analysis: gap_analysis || null,
      datapoints_stats: datapoints_stats || null,
      benchmark: benchmark || null,
    };
    sessionStorage.setItem("guestResults", JSON.stringify(formatted));
    setReady(true);
  }, [reportData]);

  if (!ready) return null;
  return <ESGDashboard reportId={reportId} />;
}
