"use client";

import { useState, useEffect, useRef } from "react";
import { Upload, FileText, Image, File, Search, CheckCircle, AlertCircle, Trash2, Loader2, FolderOpen } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

interface Document {
  id: string;
  file_name: string;
  file_url: string;
  file_size_bytes: number;
  category: string;
  description: string;
  financial_year: string;
  linked_datapoints: string[];
  linked_principles: string[];
  verified: boolean;
  expiry_date: string | null;
  created_at: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  policy: "Policy Document",
  certificate: "Certificate",
  audit_report: "Audit Report",
  data_source: "Data Source",
  board_resolution: "Board Resolution",
  photograph: "Photograph",
  other: "Other",
};

const FILE_ICONS: Record<string, typeof FileText> = {
  policy: FileText,
  certificate: CheckCircle,
  audit_report: File,
  data_source: FileText,
  board_resolution: FileText,
  photograph: Image,
  other: File,
};

function formatSize(bytes: number): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentsClient() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("all");
  const [showUploadModal, setShowUploadModal] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadCategory, setUploadCategory] = useState("data_source");
  const [uploadDescription, setUploadDescription] = useState("");
  const [uploadPrinciples, setUploadPrinciples] = useState<string[]>([]);
  const [uploadFY, setUploadFY] = useState("FY2025-26");

  useEffect(() => {
    fetchDocuments();
  }, []);

  async function fetchDocuments() {
    setLoading(true);
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      setDocs([]);
      setLoading(false);
      return;
    }

    const { data } = await supabase
      .from("documents")
      .select("*")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false });

    setDocs(data || []);
    setLoading(false);
  }

  async function handleUpload() {
    if (!uploadFile) return;
    setUploading(true);

    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) { setUploading(false); return; }

    const filePath = `${user.id}/${Date.now()}_${uploadFile.name}`;
    const { error: storageError } = await supabase.storage
      .from("documents")
      .upload(filePath, uploadFile);

    const fileUrl = storageError ? filePath : supabase.storage.from("documents").getPublicUrl(filePath).data.publicUrl;

    await supabase.from("documents").insert({
      user_id: user.id,
      file_name: uploadFile.name,
      file_url: fileUrl,
      file_size_bytes: uploadFile.size,
      mime_type: uploadFile.type,
      category: uploadCategory,
      description: uploadDescription,
      financial_year: uploadFY,
      linked_principles: uploadPrinciples,
      linked_datapoints: [],
      verified: false,
    });

    await fetchDocuments();
    resetUploadForm();
    setUploading(false);
  }

  async function handleDelete(id: string) {
    const supabase = createClient();
    await supabase.from("documents").delete().eq("id", id);
    setDocs(prev => prev.filter(d => d.id !== id));
  }

  function resetUploadForm() {
    setUploadFile(null);
    setUploadCategory("data_source");
    setUploadDescription("");
    setUploadPrinciples([]);
    setShowUploadModal(false);
  }

  const filtered = docs.filter(d => {
    const matchSearch = d.file_name.toLowerCase().includes(search.toLowerCase());
    const matchCat = catFilter === "all" || d.category === catFilter;
    return matchSearch && matchCat;
  });

  const verifiedCount = docs.filter(d => d.verified).length;
  const expiringCount = docs.filter(d => d.expiry_date && new Date(d.expiry_date) < new Date(Date.now() + 90 * 86400000)).length;

  if (loading) {
    return (
      <div className="p-6 lg:p-8 flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Document Evidence Library</h1>
          <p className="text-gray-500 text-sm mt-1">Upload and link supporting evidence to BRSR datapoints for audit-readiness</p>
        </div>
        <button onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors">
          <Upload className="w-4 h-4" /> Upload Document
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Total Documents</p>
          <p className="text-2xl font-bold">{docs.length}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Verified</p>
          <p className="text-2xl font-bold text-emerald-600">{verifiedCount}/{docs.length || 0}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Principles Covered</p>
          <p className="text-2xl font-bold text-blue-600">{new Set(docs.flatMap(d => d.linked_principles || [])).size}/9</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Expiring Soon</p>
          <p className="text-2xl font-bold text-orange-600">{expiringCount}</p>
        </div>
      </div>

      {/* Empty State */}
      {docs.length === 0 && (
        <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
          <FolderOpen className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-700 mb-2">No documents yet</h3>
          <p className="text-sm text-gray-500 mb-4 max-w-md mx-auto">
            Upload policies, certificates, audit reports, and other evidence to support your BRSR disclosures and pass audits with confidence.
          </p>
          <button onClick={() => setShowUploadModal(true)}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700">
            Upload Your First Document
          </button>
        </div>
      )}

      {/* Filters + Grid */}
      {docs.length > 0 && (
        <>
          <div className="flex gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
              <input type="text" placeholder="Search documents..." value={search} onChange={e => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm" />
            </div>
            <select value={catFilter} onChange={e => setCatFilter(e.target.value)} className="px-3 py-2 border rounded-lg text-sm">
              <option value="all">All Categories</option>
              {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map(doc => {
              const Icon = FILE_ICONS[doc.category] || File;
              return (
                <div key={doc.id} className="bg-white rounded-xl border p-4 hover:shadow-md transition-shadow group">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Icon className="w-5 h-5 text-gray-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{doc.file_name}</p>
                      <p className="text-xs text-gray-500">{CATEGORY_LABELS[doc.category] || doc.category} &bull; {formatSize(doc.file_size_bytes)}</p>
                    </div>
                    <div className="flex items-center gap-1">
                      {doc.verified ? <CheckCircle className="w-4 h-4 text-emerald-500" /> : <AlertCircle className="w-4 h-4 text-yellow-500" />}
                      <button onClick={() => handleDelete(doc.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 rounded transition-all">
                        <Trash2 className="w-3.5 h-3.5 text-red-400" />
                      </button>
                    </div>
                  </div>
                  {doc.description && <p className="text-xs text-gray-500 mt-2 line-clamp-2">{doc.description}</p>}
                  <div className="mt-3 flex flex-wrap gap-1">
                    {(doc.linked_datapoints || []).map(dp => (
                      <span key={dp} className="px-1.5 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-medium rounded">{dp}</span>
                    ))}
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <div className="flex gap-1">
                      {(doc.linked_principles || []).map(p => (
                        <span key={p} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 text-[10px] rounded">{p}</span>
                      ))}
                    </div>
                    <span className="text-[10px] text-gray-400">{doc.financial_year}</span>
                  </div>
                  {doc.expiry_date && new Date(doc.expiry_date) < new Date(Date.now() + 90 * 86400000) && (
                    <div className="mt-2 flex items-center gap-1">
                      <AlertCircle className="w-3 h-3 text-orange-500" />
                      <span className="text-[10px] text-orange-600">Expires: {doc.expiry_date}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Coverage */}
          <div className="bg-white rounded-xl border p-6">
            <h3 className="font-semibold text-gray-900 mb-3">Evidence Coverage by Principle</h3>
            <div className="grid grid-cols-9 gap-2">
              {["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9"].map(p => {
                const count = docs.filter(d => (d.linked_principles || []).includes(p)).length;
                const pct = Math.min((count / 3) * 100, 100);
                return (
                  <div key={p} className="text-center">
                    <div className="w-full bg-gray-100 rounded-full h-16 relative overflow-hidden">
                      <div className="absolute bottom-0 w-full bg-emerald-400 rounded-b-full transition-all" style={{ height: `${pct}%` }} />
                    </div>
                    <p className="text-xs font-medium text-gray-700 mt-1">{p}</p>
                    <p className="text-[10px] text-gray-500">{count}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={e => { if (e.target === e.currentTarget) resetUploadForm(); }}>
          <div className="bg-white rounded-2xl w-full max-w-lg p-6 shadow-xl">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Upload Document</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">File</label>
                <input ref={fileRef} type="file" onChange={e => setUploadFile(e.target.files?.[0] || null)}
                  accept=".pdf,.xlsx,.xls,.docx,.doc,.zip,.png,.jpg,.jpeg"
                  className="w-full text-sm border rounded-lg p-2" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">Category</label>
                  <select value={uploadCategory} onChange={e => setUploadCategory(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg text-sm">
                    {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">Financial Year</label>
                  <select value={uploadFY} onChange={e => setUploadFY(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg text-sm">
                    <option>FY2022-23</option>
                    <option>FY2023-24</option>
                    <option>FY2024-25</option>
                    <option>FY2025-26</option>
                    <option>FY2026-27</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">Description</label>
                <input type="text" value={uploadDescription} onChange={e => setUploadDescription(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="Brief description of the document" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">Linked Principles</label>
                <div className="flex flex-wrap gap-2">
                  {["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9"].map(p => (
                    <button key={p} type="button"
                      onClick={() => setUploadPrinciples(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p])}
                      className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                        uploadPrinciples.includes(p) ? "bg-emerald-100 text-emerald-800 border border-emerald-300" : "bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200"
                      }`}>
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
              <button onClick={resetUploadForm} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancel</button>
              <button onClick={handleUpload} disabled={!uploadFile || uploading}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors">
                {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                {uploading ? "Uploading..." : "Upload"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
