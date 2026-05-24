"use client";

import Link from "next/link";
import { Zap, ArrowRight, X } from "lucide-react";
import { useState } from "react";

interface Props {
  plan: string | null;
  extractionsUsed: number;
  limit: number;
}

export default function UpgradeNudge({ plan, extractionsUsed, limit }: Props) {
  const [dismissed, setDismissed] = useState(false);

  // Only show for free users who have used all or nearly all extractions
  if (dismissed) return null;
  if (plan && plan !== "free") return null;
  if (extractionsUsed < limit) return null;

  return (
    <div className="mb-6 relative overflow-hidden rounded-xl border border-amber-200 bg-gradient-to-r from-amber-50 via-yellow-50 to-orange-50 p-5">
      <button
        onClick={() => setDismissed(true)}
        className="absolute top-3 right-3 p-1 text-gray-400 hover:text-gray-600 rounded"
      >
        <X className="w-4 h-4" />
      </button>
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center flex-shrink-0">
          <Zap className="w-5 h-5 text-amber-600" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-bold text-gray-900 mb-1">
            You&apos;ve used all {limit} free extractions
          </h3>
          <p className="text-xs text-gray-600 mb-3">
            Upgrade to Growth (₹49,999/yr) for unlimited extractions and 25 suppliers, or Scale (₹1,99,999/yr) for unlimited everything.
          </p>
          <div className="flex gap-2">
            <Link
              href="/pricing"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-amber-600 text-white rounded-lg text-xs font-medium hover:bg-amber-700 transition-colors"
            >
              View Plans <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
