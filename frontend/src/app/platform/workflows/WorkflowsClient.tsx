"use client";

import { useState } from "react";
import { CheckCircle, Clock, XCircle, AlertTriangle, ArrowRight } from "lucide-react";

interface WorkflowInstance {
  id: string;
  entityType: string;
  entityName: string;
  initiatedBy: string;
  currentStep: number;
  totalSteps: number;
  status: "pending" | "in_review" | "approved" | "rejected";
  steps: { role: string; assignee: string; status: string; comment?: string; date?: string }[];
  createdAt: string;
}

const MOCK_WORKFLOWS: WorkflowInstance[] = [
  {
    id: "1", entityType: "BRSR Report", entityName: "FY2024-25 BRSR Full Report", initiatedBy: "Priya Sharma",
    currentStep: 2, totalSteps: 3, status: "in_review", createdAt: "2025-03-15",
    steps: [
      { role: "Preparer", assignee: "Priya Sharma", status: "completed", date: "2025-03-15" },
      { role: "Reviewer", assignee: "Rajesh Kumar", status: "completed", comment: "Minor edits in P6 section", date: "2025-03-18" },
      { role: "Approver", assignee: "CFO - Amit Patel", status: "pending" },
    ]
  },
  {
    id: "2", entityType: "Carbon Data", entityName: "Scope 1 Emissions Q4", initiatedBy: "Rahul Verma",
    currentStep: 1, totalSteps: 2, status: "in_review", createdAt: "2025-02-28",
    steps: [
      { role: "Data Entry", assignee: "Rahul Verma", status: "completed", date: "2025-02-28" },
      { role: "Verifier", assignee: "EHS Manager", status: "in_review" },
    ]
  },
  {
    id: "3", entityType: "Action Plan", entityName: "Renewable Energy Transition", initiatedBy: "Sneha Gupta",
    currentStep: 3, totalSteps: 3, status: "approved", createdAt: "2025-01-10",
    steps: [
      { role: "Proposer", assignee: "Sneha Gupta", status: "completed", date: "2025-01-10" },
      { role: "ESG Head", assignee: "Vikram Singh", status: "completed", comment: "Approved with budget cap ₹5Cr", date: "2025-01-15" },
      { role: "Board Committee", assignee: "CSR Committee", status: "completed", comment: "Approved in 42nd meeting", date: "2025-01-25" },
    ]
  },
  {
    id: "4", entityType: "BRSR Data", entityName: "Section A - Entity Details", initiatedBy: "Anita Roy",
    currentStep: 1, totalSteps: 2, status: "rejected", createdAt: "2025-02-20",
    steps: [
      { role: "Data Entry", assignee: "Anita Roy", status: "completed", date: "2025-02-20" },
      { role: "Reviewer", assignee: "Company Secretary", status: "rejected", comment: "CIN number incorrect, please verify from MCA portal" },
    ]
  },
  {
    id: "5", entityType: "Supplier Assessment", entityName: "Vedanta Chemicals Risk Assessment", initiatedBy: "Supply Chain Team",
    currentStep: 1, totalSteps: 3, status: "pending", createdAt: "2025-03-01",
    steps: [
      { role: "Assessor", assignee: "Supply Chain Team", status: "completed", date: "2025-03-01" },
      { role: "ESG Review", assignee: "ESG Analyst", status: "pending" },
      { role: "Procurement Head", assignee: "CPO", status: "pending" },
    ]
  },
];

const STATUS_CONFIG = {
  pending: { icon: Clock, color: "text-yellow-600", bg: "bg-yellow-50", label: "Pending" },
  in_review: { icon: AlertTriangle, color: "text-blue-600", bg: "bg-blue-50", label: "In Review" },
  approved: { icon: CheckCircle, color: "text-emerald-600", bg: "bg-emerald-50", label: "Approved" },
  rejected: { icon: XCircle, color: "text-red-600", bg: "bg-red-50", label: "Rejected" },
};

export default function WorkflowsClient() {
  const [workflows] = useState(MOCK_WORKFLOWS);
  const [statusFilter, setStatusFilter] = useState("all");

  const filtered = statusFilter === "all" ? workflows : workflows.filter(w => w.status === statusFilter);

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Sample Data Banner */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg">
        <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
        <p className="text-xs text-amber-800">Showing sample workflow data. Create workflow templates in Settings to enable approval flows for your team.</p>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Workflow Approvals</h1>
          <p className="text-gray-500 text-sm mt-1">Maker-checker workflows for BRSR data, reports, and action plans</p>
        </div>
        <button className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700">
          Configure Workflows
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Pending Approval</p>
          <p className="text-2xl font-bold text-yellow-600">{workflows.filter(w => w.status === "pending" || w.status === "in_review").length}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Approved</p>
          <p className="text-2xl font-bold text-emerald-600">{workflows.filter(w => w.status === "approved").length}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Rejected</p>
          <p className="text-2xl font-bold text-red-600">{workflows.filter(w => w.status === "rejected").length}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Total Workflows</p>
          <p className="text-2xl font-bold">{workflows.length}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {["all", "pending", "in_review", "approved", "rejected"].map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium ${statusFilter === s ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600"}`}>
            {s === "all" ? "All" : s === "in_review" ? "In Review" : s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Workflow Cards */}
      <div className="space-y-4">
        {filtered.map(wf => {
          const config = STATUS_CONFIG[wf.status];
          const StatusIcon = config.icon;
          return (
            <div key={wf.id} className="bg-white rounded-xl border p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-gray-100 rounded text-[10px] font-medium text-gray-600">{wf.entityType}</span>
                    <h3 className="text-sm font-semibold text-gray-900">{wf.entityName}</h3>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Initiated by {wf.initiatedBy} • {wf.createdAt}</p>
                </div>
                <span className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium ${config.bg} ${config.color}`}>
                  <StatusIcon className="w-3.5 h-3.5" />
                  {config.label}
                </span>
              </div>

              {/* Steps */}
              <div className="flex items-center gap-2">
                {wf.steps.map((step, i) => (
                  <div key={i} className="flex items-center gap-2 flex-1">
                    <div className={`flex-1 p-3 rounded-lg border ${step.status === "completed" ? "border-emerald-200 bg-emerald-50" : step.status === "in_review" ? "border-blue-200 bg-blue-50" : step.status === "rejected" ? "border-red-200 bg-red-50" : "border-gray-200 bg-gray-50"}`}>
                      <div className="flex items-center gap-2">
                        {step.status === "completed" ? <CheckCircle className="w-3.5 h-3.5 text-emerald-500" /> :
                         step.status === "rejected" ? <XCircle className="w-3.5 h-3.5 text-red-500" /> :
                         step.status === "in_review" ? <Clock className="w-3.5 h-3.5 text-blue-500" /> :
                         <Clock className="w-3.5 h-3.5 text-gray-400" />}
                        <span className="text-[10px] font-medium text-gray-700">{step.role}</span>
                      </div>
                      <p className="text-[10px] text-gray-500 mt-0.5">{step.assignee}</p>
                      {step.comment && <p className="text-[10px] text-gray-600 mt-1 italic">&ldquo;{step.comment}&rdquo;</p>}
                    </div>
                    {i < wf.steps.length - 1 && <ArrowRight className="w-4 h-4 text-gray-300 flex-shrink-0" />}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
