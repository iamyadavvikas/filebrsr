"use client";

import { useState } from "react";
import Navbar from "@/components/Navbar";
import { CheckCircle2, ArrowRight, Building2, FileText, Shield, Users } from "lucide-react";
import { trackEvent } from "@/lib/posthog";

const PILOT_BENEFITS = [
  { icon: FileText, title: "Unlimited BRSR Extractions", desc: "Upload unlimited reports during the pilot period" },
  { icon: Shield, title: "SEBI Filing-Ready PDF", desc: "Generate Annexure II format reports for BSE/NSE submission" },
  { icon: Users, title: "Multi-user Access", desc: "Up to 5 team members with role-based permissions" },
  { icon: Building2, title: "Dedicated Support", desc: "Direct Slack/WhatsApp channel with our team" },
];

const PILOT_CRITERIA = [
  "Listed on BSE/NSE (top 1000 by market cap)",
  "Mandatory BRSR filer (or filing voluntarily)",
  "No existing ESG consultant contract (or contract ending)",
  "Willing to provide feedback & testimonial if satisfied",
];

export default function PilotPage() {
  const [form, setForm] = useState({
    company_name: "",
    contact_name: "",
    email: "",
    designation: "",
    cin: "",
    market_cap_range: "",
    current_filing_method: "",
    pain_points: "",
  });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    trackEvent("pilot_application_submitted", {
      company: form.company_name,
      market_cap: form.market_cap_range,
    });

    try {
      await fetch("/backend/api/platform/leads/capture", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.email,
          company_name: form.company_name,
          source: "pilot_application",
          score: 95,
          readiness_level: "enterprise",
          tags: ["pilot", "high_value", "enterprise"],
          metadata: {
            contact_name: form.contact_name,
            designation: form.designation,
            cin: form.cin,
            market_cap_range: form.market_cap_range,
            current_method: form.current_filing_method,
            pain_points: form.pain_points,
          },
        }),
      });
      setSubmitted(true);
    } catch {
      // Still show success — we'll capture from analytics
      setSubmitted(true);
    }
    setLoading(false);
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-emerald-50 to-white dark:from-gray-900 dark:to-gray-950">
        <Navbar />
        <div className="max-w-2xl mx-auto px-4 py-20 text-center">
          <CheckCircle2 className="w-16 h-16 text-emerald-600 mx-auto mb-6" />
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            Application Received!
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400 mb-8">
            We&apos;ll review your application within 24 hours. Expect a call from our team to
            schedule your onboarding session.
          </p>
          <div className="bg-white dark:bg-gray-800 border rounded-xl p-6 text-left">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Next Steps:</h3>
            <ol className="space-y-2 text-gray-600 dark:text-gray-400">
              <li>1. We verify your company details (24h)</li>
              <li>2. Onboarding call — set up org + team members (30 min)</li>
              <li>3. Upload your FY24-25 annual report</li>
              <li>4. Get your SEBI-format BRSR draft in 60 seconds</li>
            </ol>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50 to-white dark:from-gray-900 dark:to-gray-950">
      <Navbar />
      <div className="max-w-6xl mx-auto px-4 py-12">
        {/* Hero */}
        <div className="text-center mb-12">
          <div className="inline-block px-4 py-1 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 rounded-full text-sm font-medium mb-4">
            Limited to 10 Companies
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-4">
            BRSR Pilot Program
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Get free access to FileBRSR&apos;s full platform for 90 days.
            File your BRSR in SEBI format — no consultant needed.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-12">
          {/* Benefits + Criteria */}
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
              What You Get (Free for 90 Days)
            </h2>
            <div className="space-y-4 mb-8">
              {PILOT_BENEFITS.map((b) => (
                <div key={b.title} className="flex gap-4 items-start">
                  <div className="w-10 h-10 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg flex items-center justify-center shrink-0">
                    <b.icon className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">{b.title}</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{b.desc}</p>
                  </div>
                </div>
              ))}
            </div>

            <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Ideal Pilot Company:</h3>
            <ul className="space-y-2">
              {PILOT_CRITERIA.map((c) => (
                <li key={c} className="flex gap-2 items-start text-sm text-gray-600 dark:text-gray-400">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                  {c}
                </li>
              ))}
            </ul>
          </div>

          {/* Application Form */}
          <div className="bg-white dark:bg-gray-800 border rounded-2xl p-8 shadow-sm">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
              Apply for Pilot Access
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Company Name *</label>
                  <input required type="text" className="w-full px-3 py-2 border rounded-lg bg-gray-50 dark:bg-gray-700 dark:border-gray-600 text-sm" value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">CIN</label>
                  <input type="text" className="w-full px-3 py-2 border rounded-lg bg-gray-50 dark:bg-gray-700 dark:border-gray-600 text-sm" placeholder="L12345MH2020PLC..." value={form.cin} onChange={(e) => setForm({ ...form, cin: e.target.value })} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Your Name *</label>
                  <input required type="text" className="w-full px-3 py-2 border rounded-lg bg-gray-50 dark:bg-gray-700 dark:border-gray-600 text-sm" value={form.contact_name} onChange={(e) => setForm({ ...form, contact_name: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Designation *</label>
                  <input required type="text" className="w-full px-3 py-2 border rounded-lg bg-gray-50 dark:bg-gray-700 dark:border-gray-600 text-sm" placeholder="CS / CFO / ESG Head" value={form.designation} onChange={(e) => setForm({ ...form, designation: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Work Email *</label>
                <input required type="email" className="w-full px-3 py-2 border rounded-lg bg-gray-50 dark:bg-gray-700 dark:border-gray-600 text-sm" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Market Cap Range</label>
                <select className="w-full px-3 py-2 border rounded-lg bg-gray-50 dark:bg-gray-700 dark:border-gray-600 text-sm" value={form.market_cap_range} onChange={(e) => setForm({ ...form, market_cap_range: e.target.value })}>
                  <option value="">Select...</option>
                  <option value="500-1000cr">₹500 - 1,000 Cr</option>
                  <option value="1000-5000cr">₹1,000 - 5,000 Cr</option>
                  <option value="5000-20000cr">₹5,000 - 20,000 Cr</option>
                  <option value="20000cr+">₹20,000+ Cr</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">How do you currently file BRSR?</label>
                <select className="w-full px-3 py-2 border rounded-lg bg-gray-50 dark:bg-gray-700 dark:border-gray-600 text-sm" value={form.current_filing_method} onChange={(e) => setForm({ ...form, current_filing_method: e.target.value })}>
                  <option value="">Select...</option>
                  <option value="consultant">External ESG Consultant</option>
                  <option value="internal_manual">Internal Team (Manual/Excel)</option>
                  <option value="first_time">First time filing</option>
                  <option value="other_tool">Other Software Tool</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Biggest pain point with BRSR?</label>
                <textarea rows={3} className="w-full px-3 py-2 border rounded-lg bg-gray-50 dark:bg-gray-700 dark:border-gray-600 text-sm" placeholder="Data collection across departments, format compliance, deadline pressure..." value={form.pain_points} onChange={(e) => setForm({ ...form, pain_points: e.target.value })} />
              </div>
              <button type="submit" disabled={loading} className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg flex items-center justify-center gap-2 transition disabled:opacity-50">
                {loading ? "Submitting..." : <>Apply for Pilot <ArrowRight className="w-4 h-4" /></>}
              </button>
              <p className="text-xs text-center text-gray-500">No credit card required. 90-day free access.</p>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
