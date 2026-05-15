import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import Navbar from "@/components/Navbar";
import Link from "next/link";
import {
  Upload,
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  CreditCard,
} from "lucide-react";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const { data: profile } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  const { data: reports } = await supabase
    .from("reports")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(20);

  const statusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "processing":
        return <Clock className="w-4 h-4 text-yellow-500 animate-pulse" />;
      case "failed":
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <>
      <Navbar user={{ email: user.email! }} />
      <main className="flex-1">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Stats cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-2xl border border-border p-6">
              <div className="flex items-center gap-3 mb-2">
                <CreditCard className="w-5 h-5" style={{ color: "#1B4D3E" }} />
                <span className="text-sm font-medium text-muted">Plan</span>
              </div>
              <p className="text-2xl font-bold text-foreground capitalize">
                {profile?.plan || "Free"}
              </p>
            </div>
            <div className="bg-white rounded-2xl border border-border p-6">
              <div className="flex items-center gap-3 mb-2">
                <FileText className="w-5 h-5" style={{ color: "#2D7A5F" }} />
                <span className="text-sm font-medium text-muted">
                  Credits Remaining
                </span>
              </div>
              <p className="text-2xl font-bold text-foreground">
                {profile?.credits_remaining ?? 0}
              </p>
            </div>
            <div className="bg-white rounded-2xl border border-border p-6">
              <div className="flex items-center gap-3 mb-2">
                <FileText className="w-5 h-5" style={{ color: "#E8B931" }} />
                <span className="text-sm font-medium text-muted">
                  Reports Processed
                </span>
              </div>
              <p className="text-2xl font-bold text-foreground">
                {reports?.length ?? 0}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-4 mb-8">
            <Link
              href="/upload"
              className="inline-flex items-center justify-center gap-2 text-white font-semibold transition-all"
              style={{ padding: "12px 24px", borderRadius: 14, background: "linear-gradient(135deg, #1B4D3E, #2D7A5F)", boxShadow: "0 4px 16px rgba(27,77,62,0.2)" }}
            >
              <Upload className="w-5 h-5" />
              Upload New Report
            </Link>
            <Link
              href="/pricing"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-white text-foreground font-medium rounded-xl border border-border hover:bg-gray-50 transition-colors"
            >
              <CreditCard className="w-5 h-5" />
              Buy More Credits
            </Link>
          </div>

          {/* Reports table */}
          <div className="bg-white rounded-2xl border border-border overflow-hidden">
            <div className="px-6 py-4 border-b border-border">
              <h2 className="text-lg font-semibold text-foreground">
                Your Reports
              </h2>
            </div>
            {reports && reports.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                        File
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                        Company
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                        Date
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {reports.map((report) => (
                      <tr key={report.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 text-sm text-foreground">
                          <div className="flex items-center gap-2">
                            <FileText className="w-4 h-4 text-muted" />
                            {report.file_name}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <div className="flex items-center gap-2">
                            {statusIcon(report.status)}
                            <span className="capitalize">{report.status}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-muted">
                          {report.company_name || "—"}
                        </td>
                        <td className="px-6 py-4 text-sm text-muted">
                          {new Date(report.created_at).toLocaleDateString(
                            "en-IN"
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm">
                          {report.status === "completed" ? (
                            <Link
                              href={`/results/${report.id}`}
                              className="text-primary hover:underline font-medium"
                            >
                              View Results
                            </Link>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="px-6 py-16 text-center">
                <FileText className="w-12 h-12 text-muted/30 mx-auto mb-4" />
                <p className="text-muted mb-4">No reports yet</p>
                <Link
                  href="/upload"
                  className="text-primary font-medium hover:underline"
                >
                  Upload your first BRSR report
                </Link>
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
