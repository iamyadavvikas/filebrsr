"use client";

import { Download } from "lucide-react";

export default function DownloadJSONButton({ data, fileName }: { data: Record<string, unknown>; fileName: string }) {
  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${fileName.replace(".pdf", "")}_brsr_data.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <button
      onClick={downloadJSON}
      className="inline-flex items-center gap-2 text-white text-sm font-semibold transition-all"
      style={{ padding: "8px 18px", borderRadius: 10, background: "#1B4D3E" }}
    >
      <Download className="w-4 h-4" />
      Download JSON
    </button>
  );
}
