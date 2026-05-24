"use client";

import Image from "next/image";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Target, Users, Globe, ArrowRight } from "lucide-react";

const team = [
  {
    name: "Vikas Yadav",
    role: "Founder & CEO",
    bio: "MTech in Safety, Health & Environment from IIT Kharagpur. BTech in Mining Engineering from UPES, Dehradun. Passionate about building technology that makes ESG compliance accessible and affordable for Indian businesses.",
    initials: "VY",
    color: "#1B4D3E",
  },
  {
    name: "Pintu Jha",
    role: "Co-founder",
    bio: "5+ years of hands-on experience in ESG compliance, sustainability reporting, and regulatory advisory. Deep domain expertise in BRSR, GRI, and supply chain ESG assessments across multiple industries.",
    initials: "PJ",
    color: "#7C3AED",
  },
];

const values = [
  {
    icon: Target,
    title: "Compliance Made Simple",
    desc: "We believe ESG compliance shouldn't require expensive consultants or months of manual work. Our AI-powered tools make it accessible to every company.",
  },
  {
    icon: Globe,
    title: "India-First Approach",
    desc: "Built specifically for SEBI BRSR requirements with India-specific emission factors, regulatory frameworks, and pricing designed for the Indian market.",
  },
  {
    icon: Users,
    title: "Scale for All",
    desc: "From Nifty 50 enterprises to SME suppliers — our platform scales from Fortune 500 compliance teams to single-person sustainability officers.",
  },
];

export default function AboutPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden" style={{ background: "linear-gradient(160deg, #0A1628 0%, #0F2847 40%, #1B4D3E 100%)" }}>
          <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px)", backgroundSize: "48px 48px" }} />
          <div className="relative max-w-5xl mx-auto px-4 sm:px-8 py-20 md:py-28 text-center">
            <p className="text-xs font-bold uppercase tracking-widest text-emerald-400 mb-4">About Us</p>
            <h1 className="text-white text-3xl md:text-5xl font-extrabold mb-5" style={{ letterSpacing: -1.5 }}>
              Building India&apos;s ESG
              <span className="block" style={{ background: "linear-gradient(120deg, #E8B931, #F59E0B)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                infrastructure
              </span>
            </h1>
            <p className="text-white/60 text-base md:text-lg max-w-2xl mx-auto leading-relaxed">
              FileBRSR is on a mission to make ESG compliance automated, affordable, and accessible for every business in India.
            </p>
          </div>
        </section>

        {/* Mission */}
        <section className="py-16 md:py-24 px-4 sm:px-8">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-extrabold text-gray-900 mb-6">Our Mission</h2>
            <p className="text-gray-600 text-lg leading-relaxed max-w-3xl mx-auto">
              SEBI mandates BRSR disclosure for India&apos;s top 1,000 listed companies, impacting over 100,000 suppliers.
              The current approach — expensive consultants, manual Excel workflows, and months of effort — doesn&apos;t scale.
              We&apos;re building the technology layer that automates BRSR filing, enables supply chain ESG assessment at scale,
              and prepares India for carbon credit trading.
            </p>
          </div>
        </section>

        {/* Values */}
        <section className="py-16 px-4 sm:px-8" style={{ background: "var(--surface)" }}>
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl font-extrabold text-gray-900 text-center mb-12">What We Stand For</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {values.map((v, i) => {
                const Icon = v.icon;
                return (
                  <div key={i} className="bg-white rounded-2xl border border-gray-200 p-8 text-center">
                    <div className="w-14 h-14 rounded-xl bg-emerald-100 flex items-center justify-center mx-auto mb-5">
                      <Icon className="w-7 h-7 text-emerald-600" />
                    </div>
                    <h3 className="text-lg font-bold text-gray-900 mb-3">{v.title}</h3>
                    <p className="text-sm text-gray-600 leading-relaxed">{v.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Team */}
        <section className="py-16 md:py-24 px-4 sm:px-8">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-extrabold text-gray-900 text-center mb-4">Our Team</h2>
            <p className="text-gray-500 text-center mb-12 max-w-lg mx-auto">
              A team combining deep ESG domain expertise with cutting-edge AI engineering.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {team.map((member) => (
                <div key={member.name} className="bg-white rounded-2xl border border-gray-200 p-8">
                  <div
                    className="w-20 h-20 rounded-full flex items-center justify-center text-white text-2xl font-bold mb-5"
                    style={{ background: member.color }}
                  >
                    {member.initials}
                  </div>
                  <h3 className="text-xl font-bold text-gray-900">{member.name}</h3>
                  <p className="text-sm font-semibold mb-3" style={{ color: member.color }}>{member.role}</p>
                  <p className="text-sm text-gray-600 leading-relaxed">{member.bio}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-16 px-4 text-center" style={{ background: "linear-gradient(160deg, #1B4D3E, #0F3D2E)" }}>
          <h2 className="text-2xl md:text-3xl font-extrabold text-white mb-4">Ready to simplify your ESG compliance?</h2>
          <p className="text-white/60 max-w-lg mx-auto mb-8">
            Start with a free assessment or explore our BRSR platform — no credit card needed.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/products"
              className="inline-flex items-center gap-2 px-6 py-3 bg-white text-emerald-800 rounded-lg font-semibold hover:bg-gray-100"
            >
              View Products <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 px-6 py-3 border border-white/30 text-white rounded-lg font-semibold hover:bg-white/10"
            >
              Contact Us <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
