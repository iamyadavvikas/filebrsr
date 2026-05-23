import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata = {
  title: "Privacy Policy — FileBRSR",
  description: "How FileBRSR collects, uses, and protects your data.",
};

export default function PrivacyPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1 py-20 px-6" style={{ background: "#FAFAFA" }}>
        <div className="max-w-3xl mx-auto bg-white rounded-2xl border border-gray-200 p-8 md:p-12">
          <h1 className="text-3xl font-bold mb-2">Privacy Policy</h1>
          <p className="text-sm text-gray-400 mb-8">Last updated: 24 May 2026</p>

          <div className="prose prose-sm prose-gray max-w-none space-y-6">
            <section>
              <h2 className="text-lg font-bold mt-6 mb-2">1. Introduction</h2>
              <p className="text-sm text-gray-600 leading-relaxed">
                FileBRSR Technologies Pvt. Ltd. (&quot;FileBRSR&quot;, &quot;we&quot;, &quot;us&quot;) is committed to protecting the privacy and security of your personal information. This policy explains how we collect, use, store, and protect data when you use our platform at filebrsr.com.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold mt-6 mb-2">2. Information We Collect</h2>
              <p className="text-sm text-gray-600 leading-relaxed"><strong>Account Information:</strong> Name, email address, company name, designation, and contact details provided during registration.</p>
              <p className="text-sm text-gray-600 leading-relaxed mt-2"><strong>Uploaded Documents:</strong> Annual reports, sustainability reports, and other PDF documents you upload for AI extraction. These are processed to extract structured ESG data.</p>
              <p className="text-sm text-gray-600 leading-relaxed mt-2"><strong>Usage Data:</strong> Pages visited, features used, extraction history, and platform interactions (via PostHog analytics).</p>
              <p className="text-sm text-gray-600 leading-relaxed mt-2"><strong>Payment Information:</strong> Billing details processed via Razorpay. We do not store credit card numbers on our servers.</p>
              <p className="text-sm text-gray-600 leading-relaxed mt-2"><strong>Assessment Data:</strong> Responses to readiness assessments, supplier self-assessments, and ESG questionnaires.</p>
            </section>

            <section>
              <h2 className="text-lg font-bold mt-6 mb-2">3. How We Use Your Data</h2>
              <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1">
                <li>To provide AI-powered BRSR extraction and report generation services</li>
                <li>To calculate ESG scores, carbon emissions, and compliance metrics</li>
                <li>To send service-related notifications (extraction complete, filing reminders, deadline alerts)</li>
                <li>To improve our AI models and extraction accuracy (anonymized and aggregated only)</li>
                <li>To generate industry benchmarks and sector-level analytics (no individual company data exposed)</li>
                <li>To process payments and manage subscriptions</li>
                <li>To respond to support requests and communicate service updates</li>
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-bold mt-6 mb-2">4. Data Storage & Security</h2>
              <p className="text-sm text-gray-600 leading-relaxed">
                All data is stored in India on AWS infrastructure (Mumbai region) and Supabase (managed PostgreSQL). We implement:
              </p>
              <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1 mt-2">
                <li>AES-256 encryption at rest for all stored data</li>
                <li>TLS 1.3 encryption for all data in transit</li>
                <li>Row-Level Security (RLS) ensuring users can only access their own data</li>
                <li>Service-role access controls for backend operations</li>
                <li>Regular security audits and vulnerability assessments</li>
                <li>Automatic data backup with point-in-time recovery</li>
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-bold mt-6 mb-2">5. Data Sharing</h2>
              <p className="text-sm text-gray-600 leading-relaxed">We do not sell your data. We share data only with:</p>
              <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1 mt-2">
                <li><strong>AI Processing:</strong> Google (Gemini), Anthropic (Claude), and Groq for document extraction — documents are processed in-memory and not retained by these providers</li>
                <li><strong>Payment Processing:</strong> Razorpay for handling subscription payments</li>
                <li><strong>Email:</strong> Resend for transactional email delivery</li>
                <li><strong>Analytics:</strong> PostHog for anonymized usage analytics (self-hosted instance)</li>
                <li><strong>Legal Requirement:</strong> When required by law, court order, or government regulation</li>
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-bold mt-6 mb-2">6. Data Retention</h2>
              <p className="text-sm text-gray-600 leading-relaxed">
                <strong>Active accounts:</strong> Data is retained as long as your account is active.<br />
                <strong>Deleted accounts:</strong> We delete your data within 30 days of account deletion request.<br />
                <strong>Uploaded PDFs:</strong> Original uploaded files are retained for 90 days after extraction, then automatically deleted. Extracted structured data is retained with your account.<br />
                <strong>Assessment responses:</strong> Retained for 3 years for regulatory compliance purposes.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold mt-6 mb-2">7. Your Rights</h2>
              <p className="text-sm text-gray-600 leading-relaxed">Under applicable Indian data protection laws, you have the right to:</p>
              <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1 mt-2">
                <li><strong>Access:</strong> Request a copy of all personal data we hold about you</li>
                <li><strong>Correction:</strong> Update or correct inaccurate personal information</li>
                <li><strong>Deletion:</strong> Request deletion of your account and associated data</li>
                <li><strong>Export:</strong> Download your data in a machine-readable format (JSON/CSV)</li>
                <li><strong>Objection:</strong> Opt out of marketing communications at any time</li>
              </ul>
              <p className="text-sm text-gray-600 leading-relaxed mt-2">
                To exercise these rights, email us at support@filebrsr.com. We will respond within 30 days.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold mt-6 mb-2">8. Cookies & Tracking</h2>
              <p className="text-sm text-gray-600 leading-relaxed">
                We use essential cookies for authentication and session management. We use PostHog for product analytics (page views, feature usage). We do not use third-party advertising cookies or trackers. You can disable non-essential cookies in your browser settings.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold mt-6 mb-2">9. Children&apos;s Privacy</h2>
              <p className="text-sm text-gray-600 leading-relaxed">
                FileBRSR is a B2B platform designed for corporate compliance professionals. We do not knowingly collect data from individuals under 18 years of age.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold mt-6 mb-2">10. Changes to This Policy</h2>
              <p className="text-sm text-gray-600 leading-relaxed">
                We may update this Privacy Policy periodically. We will notify registered users of material changes via email at least 14 days before they take effect. The &quot;Last updated&quot; date at the top reflects the most recent revision.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-bold mt-6 mb-2">11. Contact Us</h2>
              <p className="text-sm text-gray-600 leading-relaxed">
                For privacy-related questions or to exercise your data rights:<br />
                <strong>Email:</strong> support@filebrsr.com<br />
                <strong>Data Protection Officer:</strong> dpo@filebrsr.com<br />
                <strong>Address:</strong> FileBRSR Technologies Pvt. Ltd., Bengaluru, Karnataka, India
              </p>
            </section>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
