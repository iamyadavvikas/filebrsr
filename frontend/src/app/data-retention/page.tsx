import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Data Retention & Privacy Policy | FileBRSR",
  description: "FileBRSR's data retention policy in compliance with India's Digital Personal Data Protection Act (DPDPA) 2023.",
};

export default function DataRetentionPage() {
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Data Retention & Privacy Policy</h1>
        <p className="text-sm text-gray-500 mb-8">Last updated: July 2025 · Aligned with DPDPA 2023</p>

        <div className="prose prose-sm prose-gray max-w-none space-y-8">
          <section>
            <h2 className="text-lg font-bold text-gray-900 mt-8 mb-3">1. Data We Collect</h2>
            <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">Category</th>
                  <th className="px-4 py-2 text-left font-medium">Data</th>
                  <th className="px-4 py-2 text-left font-medium">Retention</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr><td className="px-4 py-2">Account</td><td className="px-4 py-2">Email, name, company</td><td className="px-4 py-2">Until account deletion</td></tr>
                <tr><td className="px-4 py-2">Uploaded PDFs</td><td className="px-4 py-2">Sustainability reports</td><td className="px-4 py-2">90 days post-extraction, then auto-deleted</td></tr>
                <tr><td className="px-4 py-2">Extraction Results</td><td className="px-4 py-2">BRSR data points, scores</td><td className="px-4 py-2">Duration of subscription + 30 days</td></tr>
                <tr><td className="px-4 py-2">Supplier Assessments</td><td className="px-4 py-2">ESG questionnaire responses</td><td className="px-4 py-2">3 years (regulatory requirement)</td></tr>
                <tr><td className="px-4 py-2">Payment Data</td><td className="px-4 py-2">Transaction IDs (no card numbers)</td><td className="px-4 py-2">7 years (tax compliance)</td></tr>
                <tr><td className="px-4 py-2">Usage Logs</td><td className="px-4 py-2">API calls, page views</td><td className="px-4 py-2">12 months</td></tr>
              </tbody>
            </table>
          </section>

          <section>
            <h2 className="text-lg font-bold text-gray-900 mt-8 mb-3">2. Legal Basis (DPDPA 2023)</h2>
            <ul className="list-disc pl-5 space-y-1 text-gray-700">
              <li><strong>Consent:</strong> You provide explicit consent during signup for data processing.</li>
              <li><strong>Legitimate Use:</strong> Processing necessary to perform our contractual obligations (BRSR extraction, scoring).</li>
              <li><strong>Legal Obligation:</strong> Retention of financial records as required under the Income Tax Act and Companies Act.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-gray-900 mt-8 mb-3">3. Your Rights (Data Principal Rights)</h2>
            <ul className="list-disc pl-5 space-y-1 text-gray-700">
              <li><strong>Right to Access:</strong> Request a copy of all personal data we hold about you.</li>
              <li><strong>Right to Correction:</strong> Update inaccurate or incomplete data via Settings.</li>
              <li><strong>Right to Erasure:</strong> Request deletion of your account and all associated data.</li>
              <li><strong>Right to Grievance Redressal:</strong> Contact our Data Protection Officer for complaints.</li>
              <li><strong>Right to Nominate:</strong> Designate a nominee to exercise your data rights.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-gray-900 mt-8 mb-3">4. Data Storage & Security</h2>
            <ul className="list-disc pl-5 space-y-1 text-gray-700">
              <li>All data stored in India (AWS ap-south-1, Mumbai region).</li>
              <li>Encrypted at rest (AES-256) and in transit (TLS 1.3).</li>
              <li>Row-Level Security (RLS) enforced at database layer — users can only access their own data.</li>
              <li>No data is shared with third parties except for payment processing (Razorpay) and email delivery (Resend).</li>
              <li>Uploaded PDFs are processed in memory and deleted from temporary storage within 24 hours.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-gray-900 mt-8 mb-3">5. Data Deletion</h2>
            <p className="text-gray-700">
              To delete your account and all data, go to <strong>Settings → Delete Account</strong> or email us at{" "}
              <a href="mailto:privacy@filebrsr.com" className="text-emerald-600 underline">privacy@filebrsr.com</a>.
              Deletion is processed within 72 hours and is irreversible.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-bold text-gray-900 mt-8 mb-3">6. Data Protection Officer</h2>
            <p className="text-gray-700">
              For any privacy concerns or data requests under DPDPA 2023:<br />
              Email: <a href="mailto:privacy@filebrsr.com" className="text-emerald-600 underline">privacy@filebrsr.com</a><br />
              Response time: Within 7 business days
            </p>
          </section>

          <section>
            <h2 className="text-lg font-bold text-gray-900 mt-8 mb-3">7. Changes to This Policy</h2>
            <p className="text-gray-700">
              We may update this policy to reflect changes in law or our practices. Material changes will be communicated via email to all registered users at least 30 days before taking effect.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
