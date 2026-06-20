"use client";

import { useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Mail, MapPin, Clock, Send, CheckCircle2 } from "lucide-react";

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", subject: "", message: "" });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    // Open mailto with pre-filled subject and body
    const mailto = `mailto:support@filebrsr.com?subject=${encodeURIComponent(form.subject || "Inquiry from website")}&body=${encodeURIComponent(`Name: ${form.name}\nEmail: ${form.email}\n\n${form.message}`)}`;
    window.location.href = mailto;
    setSubmitted(true);
  }

  return (
    <>
      <Navbar />
      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden" style={{ background: "linear-gradient(135deg, #ECFDF5 0%, #EFF6FF 48%, #F5F3FF 100%)" }}>
          <div className="blob-wrap" style={{ top: "-110px", left: "-70px" }}>
            <div className="blob" style={{ width: 340, height: 340, background: "radial-gradient(circle at 30% 30%, #34D399, #10B981)" }} />
          </div>
          <div className="blob-wrap" style={{ top: "0", right: "-90px" }}>
            <div className="blob" style={{ width: 280, height: 280, background: "radial-gradient(circle at 30% 30%, #38BDF8, #6366F1)", animationDelay: "-5s" }} />
          </div>
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(15,23,42,0.04) 1px, transparent 1px)", backgroundSize: "40px 40px" }} />
          <div className="relative max-w-5xl mx-auto px-4 sm:px-8 py-20 md:py-28 text-center">
            <div className="inline-flex items-center gap-2 mb-6 backdrop-blur-sm fade-up" style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.4, textTransform: "uppercase", background: "rgba(255,255,255,0.7)", color: "#059669", padding: "8px 18px", borderRadius: 24, border: "1px solid rgba(16,185,129,0.25)", boxShadow: "0 4px 16px rgba(16,185,129,0.08)", animationFillMode: "both" }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#10B981", display: "inline-block", animation: "pulse 2s infinite" }} />
              Contact Us
            </div>
            <h1 className="fade-up" style={{ fontSize: "clamp(34px, 5vw, 56px)", fontWeight: 800, lineHeight: 1.08, marginBottom: 20, letterSpacing: -1.5, animationDelay: "80ms", animationFillMode: "both" }}>
              <span className="gradient-text" style={{ backgroundImage: "linear-gradient(110deg, #10B981 0%, #06B6D4 45%, #6366F1 100%)" }}>
                Get in touch
              </span>
            </h1>
            <p className="fade-up" style={{ fontSize: 18, color: "#475569", maxWidth: 640, lineHeight: 1.7, margin: "0 auto", animationDelay: "160ms", animationFillMode: "both" }}>
              Have questions about BRSR compliance, our platform, or pricing? We&apos;d love to hear from you.
            </p>
          </div>
        </section>

        {/* Contact Content */}
        <section className="py-16 md:py-24 px-4 sm:px-8">
          <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-12">
            {/* Contact Info */}
            <div>
              <h2 className="text-2xl font-extrabold text-gray-900 mb-6">Reach Out</h2>
              <p className="text-gray-600 leading-relaxed mb-8">
                Whether you&apos;re a listed company looking to automate BRSR filing, an SME supplier wanting to prove ESG readiness,
                or simply curious about how FileBRSR can help — drop us a line.
              </p>

              <div className="space-y-6">
                <div className="flex items-start gap-4">
                  <div className="w-11 h-11 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0">
                    <Mail className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900 text-sm">Email</p>
                    <a href="mailto:support@filebrsr.com" className="text-emerald-600 hover:underline">
                      support@filebrsr.com
                    </a>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="w-11 h-11 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0">
                    <MapPin className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900 text-sm">Location</p>
                    <p className="text-gray-600 text-sm">India</p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="w-11 h-11 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0">
                    <Clock className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900 text-sm">Response Time</p>
                    <p className="text-gray-600 text-sm">We typically respond within 24 hours</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Contact Form */}
            <div className="bg-white rounded-2xl border border-gray-200 p-8">
              {submitted ? (
                <div className="text-center py-12">
                  <CheckCircle2 className="w-14 h-14 text-emerald-500 mx-auto mb-4" />
                  <h3 className="text-lg font-bold text-gray-900 mb-2">Message Ready!</h3>
                  <p className="text-sm text-gray-500">Your email client should open with the message. You can also email us directly at support@filebrsr.com</p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Name</label>
                    <input
                      type="text"
                      required
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                      placeholder="Your name"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
                    <input
                      type="email"
                      required
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                      placeholder="you@company.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Subject</label>
                    <input
                      type="text"
                      value={form.subject}
                      onChange={(e) => setForm({ ...form, subject: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                      placeholder="BRSR compliance inquiry"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Message</label>
                    <textarea
                      required
                      rows={4}
                      value={form.message}
                      onChange={(e) => setForm({ ...form, message: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 resize-none"
                      placeholder="Tell us how we can help..."
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full flex items-center justify-center gap-2 px-5 py-3 bg-emerald-600 text-white rounded-lg font-semibold text-sm hover:bg-emerald-700 transition-colors"
                  >
                    <Send className="w-4 h-4" />
                    Send Message
                  </button>
                </form>
              )}
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
