"use client";

import { useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Loader2 } from "lucide-react";

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
    desc: "For suppliers / SMEs getting assessed",
    reports: "Unlimited self-assessments",
    features: ["ESG self-assessment", "Basic scorecard", "1 shareable badge", "Industry benchmark", "3 AI extractions"],
    cta: "Start Free",
    popular: false,
    ctaBg: "white", ctaColor: "#1B4D3E", ctaBorder: "1px solid #E5E7DF",
  },
  {
    key: "pro",
    name: "Pro",
    price: "₹50,000",
    period: "/year",
    monthlyEquiv: "₹4,167/month",
    desc: "For mid-size companies assessing suppliers",
    reports: "25 suppliers + 10 AI reports/month",
    features: [
      "Assess 25 suppliers",
      "Full BRSR filing (AI extraction)",
      "10 AI reports per month",
      "Gap analysis & scoring",
      "Multi-framework mapping (GRI, CDP, TCFD)",
      "NIFTY 50 sector benchmarks",
      "Carbon calculator",
      "PDF + XBRL-JSON export",
      "Email support",
    ],
    cta: "Subscribe",
    popular: true,
    ctaBg: "#1B4D3E", ctaColor: "white", ctaBorder: "none",
  },
  {
    key: "enterprise",
    name: "Enterprise",
    price: "₹5-15L",
    period: "/year",
    desc: "For listed companies with large supply chains",
    reports: "Unlimited suppliers + reports",
    features: [
      "Unlimited suppliers",
      "Unlimited AI reports",
      "Everything in Pro +",
      "API & SAP integration",
      "XBRL filing generation",
      "Workflow approvals (maker-checker)",
      "Multi-user + SSO",
      "Audit trail & compliance",
      "White-label option",
      "Dedicated account manager",
      "SLA guarantee",
    ],
    cta: "Contact Sales",
    popular: false,
    ctaBg: "#E8B931", ctaColor: "#1B4D3E", ctaBorder: "none",
  },
];

const comparisonData = [
  { feature: "Supplier assessments", free: "Self only", pro: "25 suppliers", enterprise: "Unlimited" },
  { feature: "AI report extractions", free: "3 total", pro: "10/month", enterprise: "Unlimited" },
  { feature: "ESG scorecard & badge", free: "✓", pro: "✓", enterprise: "✓" },
  { feature: "Gap analysis", free: "Basic", pro: "Full", enterprise: "Full" },
  { feature: "Multi-framework mapping", free: "—", pro: "✓", enterprise: "✓" },
  { feature: "NIFTY 50 benchmarks", free: "—", pro: "✓", enterprise: "✓" },
  { feature: "Carbon calculator", free: "—", pro: "✓", enterprise: "✓" },
  { feature: "XBRL filing", free: "—", pro: "—", enterprise: "✓" },
  { feature: "Workflow approvals", free: "—", pro: "—", enterprise: "✓" },
  { feature: "API access", free: "—", pro: "—", enterprise: "✓" },
  { feature: "Users", free: "1", pro: "5", enterprise: "Unlimited + SSO" },
  { feature: "Support", free: "Community", pro: "Email", enterprise: "Dedicated" },
];

export default function PricingPage() {
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  const handlePurchase = async (planKey: string) => {
    if (planKey === "free") {
      window.location.href = "/upload";
      return;
    }
    if (planKey === "enterprise") {
      window.location.href = "mailto:sales@filebrsr.com?subject=Enterprise%20Plan%20Inquiry";
      return;
    }

    setLoadingPlan(planKey);
    try {
      const isSubscription = planKey === "pro";
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const endpoint = isSubscription
        ? `${backendUrl}/api/billing/create-subscription`
        : `${backendUrl}/api/billing/create-order`;

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan: planKey, billing_period: "yearly", user_id: "guest" }),
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
          await fetch(`${backendUrl}/api/billing/verify-payment`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              razorpay_order_id: response.razorpay_order_id || "",
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              user_id: "guest",
              plan: planKey,
            }),
          });
          window.location.href = "/dashboard";
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
        <section style={{ padding: "72px 28px 48px", background: "var(--highlight-bg)" }}>
          <div className="max-w-[960px] mx-auto text-center">
            <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color: "var(--primary-light)", marginBottom: 8 }}>
              Pricing
            </p>
            <h1 style={{ fontSize: 38, fontWeight: 800, marginBottom: 12, letterSpacing: -1, color: "var(--foreground)" }}>
              Replace ₹15L consultants with one tool
            </h1>
            <p style={{ fontSize: 16, maxWidth: 520, margin: "0 auto 8px", lineHeight: 1.6, color: "var(--muted)" }}>
              Companies pay ₹5-15 lakhs annually for manual BRSR compilation. FileBRSR does it in seconds.
            </p>
            <div className="flex justify-center gap-6 mt-6" style={{ fontSize: 13, color: "var(--muted)" }}>
              <span>✓ No credit card for free tier</span>
              <span>✓ Cancel anytime</span>
              <span>✓ GST invoice included</span>
            </div>
          </div>
        </section>

        {/* Plans Grid */}
        <section style={{ padding: "0 28px 64px" }}>
          <div className="max-w-[1100px] mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5" style={{ alignItems: "start" }}>
              {plans.map((p) => (
                <div
                  key={p.key}
                  className="relative flex flex-col"
                  style={{
                    borderRadius: 20,
                    border: p.popular ? "2px solid var(--primary)" : "1px solid var(--border)",
                    padding: "28px 24px",
                    background: "var(--card)",
                    boxShadow: p.popular ? "0 12px 40px rgba(27,77,62,0.12)" : "0 2px 8px rgba(0,0,0,0.04)",
                  }}
                >
                  {p.popular && (
                    <div
                      className="absolute"
                      style={{
                        top: -13, left: "50%", transform: "translateX(-50%)",
                        background: "#1B4D3E", color: "white",
                        fontSize: 11, fontWeight: 700, padding: "5px 16px",
                        borderRadius: 20, letterSpacing: 0.5,
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

            {/* Pay-per-report callout */}
            <div
              className="mt-8 flex flex-col md:flex-row items-center justify-between gap-6"
              style={{ border: "1px solid var(--border)", borderRadius: 20, padding: "28px 32px", background: "var(--card)" }}
            >
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4, color: "var(--foreground)" }}>
                  Just need one report? <span style={{ color: "var(--primary-light)" }}>₹2,500 per report</span>
                </h3>
                <p style={{ fontSize: 14, color: "var(--muted)" }}>
                  Full analysis with NIFTY 50 benchmarks, ESRS mapping, and branded PDF — no subscription needed.
                </p>
              </div>
              <button
                onClick={() => handlePurchase("pay_per_report")}
                disabled={loadingPlan === "pay_per_report"}
                className="flex items-center gap-2 whitespace-nowrap"
                style={{
                  padding: "12px 28px", borderRadius: 12, fontSize: 14, fontWeight: 700,
                  border: "2px solid var(--primary-light)", background: "var(--card)", color: "var(--primary-light)", cursor: "pointer",
                }}
              >
                {loadingPlan === "pay_per_report" && <Loader2 className="w-4 h-4 animate-spin" />}
                Buy Single Report
              </button>
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
                    <th style={{ padding: "14px 16px", textAlign: "center", fontSize: 13, fontWeight: 600, color: "var(--primary)" }}>Pro</th>
                    <th style={{ padding: "14px 16px", textAlign: "center", fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>Enterprise</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonData.map((row, i) => (
                    <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
                      <td style={{ padding: "12px 16px", fontSize: 13, fontWeight: 500, color: "var(--foreground)" }}>{row.feature}</td>
                      <td style={{ padding: "12px 16px", fontSize: 13, textAlign: "center", color: "var(--muted)" }}>{row.free}</td>
                      <td style={{ padding: "12px 16px", fontSize: 13, textAlign: "center", fontWeight: 600, color: "var(--primary)" }}>{row.pro}</td>
                      <td style={{ padding: "12px 16px", fontSize: 13, textAlign: "center", color: "var(--muted)" }}>{row.enterprise}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* BRSR Deadline CTA */}
        <section className="text-center" style={{ padding: "56px 28px", background: "linear-gradient(135deg, #1B4D3E, #2D7A5F)" }}>
          <div className="max-w-[600px] mx-auto text-white">
            <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", opacity: 0.7, marginBottom: 12 }}>
              Compliance Deadline
            </div>
            <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 12 }}>
              BRSR Core + Assurance mandatory from FY 2026-27
            </h2>
            <p style={{ fontSize: 15, opacity: 0.8, lineHeight: 1.65, marginBottom: 28 }}>
              SEBI mandates BRSR Core with third-party assurance for the top 250 companies. 
              All 1,000 listed companies by 2027-28. Start your compliance journey today.
            </p>
            <Link
              href="/upload"
              className="inline-block"
              style={{ fontSize: 15, fontWeight: 700, padding: "14px 36px", borderRadius: 14, background: "#E8B931", color: "#1B4D3E" }}
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
