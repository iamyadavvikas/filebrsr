"use client";

import { useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Loader2 } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

declare global {
  interface Window {
    Razorpay: new (options: RazorpayOptions) => RazorpayInstance;
  }
}

interface RazorpayOptions {
  key: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  order_id?: string;
  subscription_id?: string;
  handler: (response: RazorpayResponse) => void;
  theme: { color: string };
}

interface RazorpayInstance {
  open: () => void;
}

interface RazorpayResponse {
  razorpay_order_id?: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
  razorpay_subscription_id?: string;
}

const plans = [
  {
    key: "free",
    name: "Free",
    price: "₹0",
    period: "forever",
    desc: "Get started — assess up to 5 suppliers free",
    reports: "3 AI extractions + 5 suppliers",
    features: [
      "5 supplier ESG assessments",
      "3 AI BRSR extractions (one-time)",
      "Scope 1 & 2 carbon calculator",
      "Basic gap analysis & scoring",
      "Shareable ESG badge",
      "Industry benchmarks",
    ],
    cta: "Start Free",
    popular: false,
    ctaBg: "white", ctaColor: "#1B4D3E", ctaBorder: "1px solid #E5E7DF",
  },
  {
    key: "growth",
    name: "Growth",
    price: "₹49,999",
    period: "/year",
    monthlyEquiv: "₹4,167/month",
    desc: "For listed companies scaling supplier oversight",
    reports: "Unlimited extractions + 25 suppliers + Scope 3",
    features: [
      "25 supplier assessments",
      "Unlimited AI BRSR extractions",
      "Full Scope 1, 2 & 3 carbon",
      "Multi-framework mapping (GRI, CDP, TCFD, SASB)",
      "NIFTY 50 sector benchmarks",
      "PDF + XBRL-JSON export",
      "5 users",
      "Priority email support",
    ],
    cta: "Subscribe",
    popular: true,
    ctaBg: "linear-gradient(120deg, #10B981, #06B6D4)", ctaColor: "white", ctaBorder: "none",
  },
  {
    key: "scale",
    name: "Scale",
    price: "₹1,99,999",
    period: "/year",
    monthlyEquiv: "₹16,667/month",
    desc: "For enterprises with large supply chains",
    reports: "Unlimited suppliers + XBRL filing + audit",
    features: [
      "Everything in Growth +",
      "Unlimited supplier assessments",
      "XBRL filing generation",
      "Audit trail & compliance log",
      "Supplier-side dashboard (coming soon)",
      "10 users",
      "Dedicated account manager",
    ],
    cta: "Subscribe",
    popular: false,
    ctaBg: "white", ctaColor: "#1B4D3E", ctaBorder: "1px solid #E5E7DF",
  },
  {
    key: "enterprise",
    name: "Enterprise",
    price: "Custom",
    period: "",
    desc: "For conglomerates with 500+ suppliers across BUs",
    reports: "Custom limits + API + SSO",
    features: [
      "Everything in Scale +",
      "API & ERP integration",
      "SSO / SAML login",
      "Workflow approvals (maker-checker)",
      "White-label option",
      "SLA guarantee",
      "Unlimited users",
    ],
    cta: "Contact Sales",
    popular: false,
    ctaBg: "linear-gradient(120deg, #06B6D4, #6366F1)", ctaColor: "white", ctaBorder: "none",
  },
];

const comparisonData = [
  { feature: "AI BRSR extractions", free: "3 (one-time)", growth: "Unlimited", scale: "Unlimited", enterprise: "Unlimited" },
  { feature: "Supplier assessments", free: "5", growth: "25", scale: "Unlimited", enterprise: "Unlimited" },
  { feature: "Carbon calculator", free: "Scope 1 & 2", growth: "Scope 1, 2 & 3", scale: "Scope 1, 2 & 3", enterprise: "Scope 1, 2 & 3" },
  { feature: "ESG scorecard & badge", free: "✓", growth: "✓", scale: "✓", enterprise: "✓" },
  { feature: "Gap analysis", free: "Basic", growth: "Full", scale: "Full", enterprise: "Full" },
  { feature: "Multi-framework mapping", free: "—", growth: "✓", scale: "✓", enterprise: "✓" },
  { feature: "NIFTY 50 benchmarks", free: "—", growth: "✓", scale: "✓", enterprise: "✓" },
  { feature: "XBRL filing", free: "—", growth: "Export only", scale: "Full generation", enterprise: "Full generation" },
  { feature: "Supplier dashboard", free: "—", growth: "—", scale: "✓", enterprise: "✓" },
  { feature: "Audit trail", free: "—", growth: "—", scale: "✓", enterprise: "✓" },
  { feature: "API access", free: "—", growth: "—", scale: "—", enterprise: "✓" },
  { feature: "Users", free: "1", growth: "5", scale: "10", enterprise: "Unlimited (SSO)" },
  { feature: "Support", free: "Community", growth: "Priority email", scale: "Dedicated AM", enterprise: "Dedicated + SLA" },
];

export default function PricingPage() {
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  const handlePurchase = async (planKey: string) => {
    if (planKey === "free") {
      window.location.href = "/platform/supply-chain";
      return;
    }
    if (planKey === "enterprise") {
      window.location.href = "mailto:sales@filebrsr.com?subject=Enterprise%20Plan%20Inquiry";
      return;
    }

    setLoadingPlan(planKey);
    try {
      // Require authenticated user before checkout — entitlement bound to JWT
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        const next = encodeURIComponent(`/pricing?plan=${planKey}`);
        window.location.href = `/login?next=${next}`;
        setLoadingPlan(null);
        return;
      }

      const isSubscription = planKey === "growth" || planKey === "scale";
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const endpoint = isSubscription
        ? `${backendUrl}/api/billing/create-subscription`
        : `${backendUrl}/api/billing/create-order`;

      const res = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ plan: planKey, billing_period: "yearly" }),
      });

      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "Failed to create order");
        setLoadingPlan(null);
        return;
      }

      const options: RazorpayOptions = {
        key: data.key_id,
        amount: data.amount,
        currency: data.currency || "INR",
        name: "FileBRSR",
        description: `${planKey.charAt(0).toUpperCase() + planKey.slice(1)} Plan`,
        handler: async (response: RazorpayResponse) => {
          const verifyRes = await fetch(`${backendUrl}/api/billing/verify-payment`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${session.access_token}`,
            },
            body: JSON.stringify({
              razorpay_order_id: response.razorpay_order_id || null,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              razorpay_subscription_id: response.razorpay_subscription_id || null,
            }),
          });
          if (!verifyRes.ok) {
            const err = await verifyRes.json().catch(() => ({}));
            alert(`Payment verification failed: ${err.detail || verifyRes.statusText}. Please contact support.`);
            return;
          }
          window.location.href = "/platform?upgraded=1";
        },
        theme: { color: "#1B4D3E" },
      };

      if (data.type === "subscription") {
        options.subscription_id = data.subscription_id;
      } else {
        options.order_id = data.order_id;
      }

      const rzp = new window.Razorpay(options);
      rzp.open();
    } catch {
      alert("Something went wrong. Please try again.");
    } finally {
      setLoadingPlan(null);
    }
  };

  return (
    <>
      <Navbar />
      <main className="flex-1">
        {/* Header */}
        <section className="relative overflow-hidden" style={{ background: "linear-gradient(135deg, #ECFDF5 0%, #EFF6FF 48%, #F5F3FF 100%)" }}>
          <div className="blob-wrap" style={{ top: "-110px", left: "-70px" }}>
            <div className="blob" style={{ width: 340, height: 340, background: "radial-gradient(circle at 30% 30%, #34D399, #10B981)" }} />
          </div>
          <div className="blob-wrap" style={{ top: "0", right: "-90px" }}>
            <div className="blob" style={{ width: 280, height: 280, background: "radial-gradient(circle at 30% 30%, #38BDF8, #6366F1)", animationDelay: "-5s" }} />
          </div>
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(15,23,42,0.04) 1px, transparent 1px)", backgroundSize: "40px 40px" }} />
          <div className="relative max-w-[960px] mx-auto px-7 pt-20 pb-12 md:pt-24 text-center">
            <div className="inline-flex items-center gap-2 mb-6 backdrop-blur-sm fade-up" style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.4, textTransform: "uppercase", background: "rgba(255,255,255,0.7)", color: "#059669", padding: "8px 18px", borderRadius: 24, border: "1px solid rgba(16,185,129,0.25)", boxShadow: "0 4px 16px rgba(16,185,129,0.08)", animationFillMode: "both" }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#10B981", display: "inline-block", animation: "pulse 2s infinite" }} />
              Pricing
            </div>
            <h1 className="fade-up" style={{ fontSize: "clamp(32px, 4.5vw, 48px)", fontWeight: 800, marginBottom: 16, letterSpacing: -1.5, color: "#0F172A", lineHeight: 1.1, animationDelay: "80ms", animationFillMode: "both" }}>
              Replace ₹15L consultants
              <span className="gradient-text" style={{ display: "block", backgroundImage: "linear-gradient(110deg, #10B981 0%, #06B6D4 45%, #6366F1 100%)" }}>
                with one platform
              </span>
            </h1>
            <p className="fade-up" style={{ fontSize: 17, maxWidth: 540, margin: "0 auto 8px", lineHeight: 1.7, color: "#475569", animationDelay: "160ms", animationFillMode: "both" }}>
              Companies pay ₹5-15 lakhs annually for manual BRSR compilation. FileBRSR does it in seconds.
            </p>
            <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 mt-6 fade-up" style={{ fontSize: 13, color: "#64748B", animationDelay: "240ms", animationFillMode: "both" }}>
              <span>✓ No credit card for free tier</span>
              <span>✓ Cancel anytime</span>
              <span>✓ GST invoice included</span>
            </div>
            <p className="mt-4 text-center fade-up" style={{ fontSize: 12, color: "#64748B", opacity: 0.7, animationDelay: "300ms", animationFillMode: "both" }}>
              Used by compliance teams preparing FY2025-26 and FY2026-27 BRSR filings
            </p>
          </div>
        </section>

        {/* Plans Grid */}
        <section style={{ padding: "0 28px 64px" }}>
          <div className="max-w-[1100px] mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5" style={{ alignItems: "start" }}>
              {plans.map((p) => (
                <div
                  key={p.key}
                  className="relative flex flex-col card-hover"
                  style={{
                    borderRadius: 20,
                    border: p.popular ? "2px solid #10B981" : "1px solid var(--border)",
                    padding: "28px 24px",
                    background: "var(--card)",
                    boxShadow: p.popular ? "0 16px 44px rgba(16,185,129,0.18)" : "0 2px 8px rgba(0,0,0,0.04)",
                  }}
                >
                  {p.popular && (
                    <div
                      className="absolute"
                      style={{
                        top: -13, left: "50%", transform: "translateX(-50%)",
                        background: "linear-gradient(120deg, #10B981, #06B6D4)", color: "white",
                        fontSize: 11, fontWeight: 700, padding: "5px 16px",
                        borderRadius: 20, letterSpacing: 0.5,
                        boxShadow: "0 6px 18px rgba(16,185,129,0.3)",
                      }}
                    >
                      Most Popular
                    </div>
                  )}
                  <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4, color: "var(--foreground)" }}>{p.name}</h3>
                  <p style={{ fontSize: 13, marginBottom: 16, color: "var(--muted)" }}>{p.desc}</p>
                  <div style={{ marginBottom: 8 }}>
                    <span style={{ fontSize: 32, fontWeight: 800, letterSpacing: -1, color: "var(--foreground)" }}>{p.price}</span>
                    {p.period && <span style={{ fontSize: 14, marginLeft: 4, color: "var(--muted)" }}>{p.period}</span>}
                  </div>
                  {"monthlyEquiv" in p && p.monthlyEquiv && (
                    <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 12 }}>{p.monthlyEquiv}</p>
                  )}
                  <div style={{ background: "#F0FDF4", borderRadius: 10, padding: "8px 12px", marginBottom: 20, fontSize: 13, fontWeight: 600, color: "#166534" }}>
                    {p.reports}
                  </div>
                  <button
                    onClick={() => handlePurchase(p.key)}
                    disabled={loadingPlan === p.key}
                    className="flex items-center justify-center gap-2 transition-all w-full"
                    style={{
                      padding: "12px 20px", borderRadius: 12, fontSize: 14, fontWeight: 700,
                      border: p.ctaBorder, background: p.ctaBg, color: p.ctaColor,
                      cursor: "pointer", marginBottom: 20,
                    }}
                  >
                    {loadingPlan === p.key && <Loader2 className="w-4 h-4 animate-spin" />}
                    {p.cta}
                  </button>
                  <div className="flex flex-col gap-2.5 flex-1">
                    {p.features.map((f) => (
                      <div key={f} className="flex items-start gap-2" style={{ fontSize: 13, color: "var(--muted)" }}>
                        <span style={{ color: "var(--success)", fontWeight: 700, fontSize: 14, flexShrink: 0 }}>✓</span>
                        {f}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

          </div>
        </section>

        {/* Comparison Table */}
        <section style={{ padding: "48px 28px 72px", background: "var(--warm)" }}>
          <div className="max-w-[960px] mx-auto">
            <h2 className="text-center" style={{ fontSize: 26, fontWeight: 800, marginBottom: 32, color: "var(--foreground)" }}>
              Compare plans
            </h2>
            <div className="overflow-x-auto" style={{ borderRadius: 16, border: "1px solid var(--border)" }}>
              <table className="w-full" style={{ background: "var(--card)", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "var(--surface)" }}>
                    <th style={{ padding: "14px 16px", textAlign: "left", fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>Feature</th>
                    <th style={{ padding: "14px 16px", textAlign: "center", fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>Free</th>
                    <th style={{ padding: "14px 16px", textAlign: "center", fontSize: 13, fontWeight: 600, color: "var(--primary)" }}>Growth</th>
                    <th style={{ padding: "14px 16px", textAlign: "center", fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>Scale</th>
                    <th style={{ padding: "14px 16px", textAlign: "center", fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>Enterprise</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonData.map((row, i) => (
                    <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
                      <td style={{ padding: "12px 16px", fontSize: 13, fontWeight: 500, color: "var(--foreground)" }}>{row.feature}</td>
                      <td style={{ padding: "12px 16px", fontSize: 13, textAlign: "center", color: "var(--muted)" }}>{row.free}</td>
                      <td style={{ padding: "12px 16px", fontSize: 13, textAlign: "center", fontWeight: 600, color: "var(--primary)" }}>{row.growth}</td>
                      <td style={{ padding: "12px 16px", fontSize: 13, textAlign: "center", color: "var(--muted)" }}>{row.scale}</td>
                      <td style={{ padding: "12px 16px", fontSize: 13, textAlign: "center", color: "var(--muted)" }}>{row.enterprise}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* BRSR Deadline CTA */}
        <section className="relative overflow-hidden text-center" style={{ padding: "56px 28px", background: "linear-gradient(135deg, #10B981 0%, #06B6D4 50%, #6366F1 100%)" }}>
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(255,255,255,0.08) 1px, transparent 1px)", backgroundSize: "32px 32px" }} />
          <div className="relative max-w-[600px] mx-auto text-white">
            <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", opacity: 0.85, marginBottom: 12 }}>
              Compliance Deadline
            </div>
            <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 12 }}>
              BRSR Core + Assurance mandatory from FY 2026-27
            </h2>
            <p style={{ fontSize: 15, opacity: 0.9, lineHeight: 1.65, marginBottom: 28 }}>
              SEBI mandates BRSR Core with third-party assurance for the top 250 companies. 
              All 1,000 listed companies by 2027-28. Start your compliance journey today.
            </p>
            <Link
              href="/upload"
              className="inline-block"
              style={{ fontSize: 15, fontWeight: 700, padding: "14px 36px", borderRadius: 14, background: "white", color: "#0891B2", boxShadow: "0 10px 30px rgba(8,145,178,0.25)" }}
            >
              Start Compliance Check →
            </Link>
          </div>
        </section>
      </main>
      <Footer />
      <script src="https://checkout.razorpay.com/v1/checkout.js" async />
    </>
  );
}
