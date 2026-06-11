import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

function getAdminClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

// POST /api/suppliers/assess - submit supplier self-assessment
export async function POST(req: NextRequest) {
  const body = await req.json();
  const { assessment_id, responses } = body;

  if (!assessment_id || !responses) {
    return NextResponse.json({ error: "assessment_id and responses required" }, { status: 400 });
  }

  const admin = getAdminClient();

  // Fetch assessment to validate it exists
  const { data: assessment, error: fetchErr } = await admin
    .from("supplier_assessments")
    .select("id, supplier_id, overall_score")
    .eq("id", assessment_id)
    .single();

  if (fetchErr || !assessment) {
    return NextResponse.json({ error: "Assessment not found" }, { status: 404 });
  }

  // Already completed?
  if (assessment.overall_score !== null) {
    return NextResponse.json({ error: "Assessment already completed" }, { status: 400 });
  }

  // Calculate scores from responses
  const scores = calculateScores(responses);

  // Update assessment with responses and scores
  const { error: updateErr } = await admin
    .from("supplier_assessments")
    .update({
      responses,
      environment_score: scores.environment,
      social_score: scores.social,
      governance_score: scores.governance,
      overall_score: scores.overall,
      assessed_at: new Date().toISOString(),
    })
    .eq("id", assessment_id);

  if (updateErr) {
    return NextResponse.json({ error: updateErr.message }, { status: 500 });
  }

  // Update supplier's ESG score and risk level
  const riskLevel = scores.overall >= 70 ? "low" : scores.overall >= 50 ? "medium" : scores.overall >= 30 ? "high" : "critical";

  await admin
    .from("suppliers")
    .update({
      esg_score: scores.overall,
      risk_level: riskLevel,
      last_assessed_at: new Date().toISOString(),
      status: "active",
    })
    .eq("id", assessment.supplier_id);

  return NextResponse.json({
    success: true,
    scores,
    risk_level: riskLevel,
  });
}

// GET /api/suppliers/assess?id=xxx - get assessment questionnaire
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");

  if (!id) return NextResponse.json({ error: "Assessment id required" }, { status: 400 });

  const admin = getAdminClient();
  const { data, error } = await admin
    .from("supplier_assessments")
    .select("id, supplier_id, financial_year, assessment_type, overall_score, suppliers(name, industry)")
    .eq("id", id)
    .single();

  if (error || !data) return NextResponse.json({ error: "Not found" }, { status: 404 });

  // Return questionnaire template
  return NextResponse.json({
    assessment: data,
    questionnaire: ESG_QUESTIONNAIRE,
  });
}

// ESG Questionnaire for suppliers (BRSR-aligned)
const ESG_QUESTIONNAIRE = {
  sections: [
    {
      id: "environment",
      title: "Environment",
      description: "Environmental policies, emissions, and resource management",
      questions: [
        { id: "env_1", question: "Does your company have a documented environmental policy?", type: "yesno", weight: 5 },
        { id: "env_2", question: "Do you measure and report GHG emissions (Scope 1 & 2)?", type: "yesno", weight: 10 },
        { id: "env_3", question: "What percentage of energy comes from renewable sources?", type: "percentage", weight: 10 },
        { id: "env_4", question: "Do you have waste reduction targets?", type: "yesno", weight: 5 },
        { id: "env_5", question: "Have you implemented water recycling/reuse?", type: "yesno", weight: 5 },
        { id: "env_6", question: "Do you have environmental certifications (ISO 14001, etc.)?", type: "yesno", weight: 8 },
        { id: "env_7", question: "What is your estimated carbon intensity (tCO2e per ₹Cr revenue)?", type: "number", weight: 7 },
      ],
    },
    {
      id: "social",
      title: "Social",
      description: "Labor practices, safety, diversity, and community impact",
      questions: [
        { id: "soc_1", question: "Do you have a health & safety management system (ISO 45001)?", type: "yesno", weight: 8 },
        { id: "soc_2", question: "What was your LTIFR (Lost Time Injury Frequency Rate) last year?", type: "number", weight: 7 },
        { id: "soc_3", question: "What percentage of workforce is female?", type: "percentage", weight: 5 },
        { id: "soc_4", question: "Do you provide annual ESG/sustainability training to employees?", type: "yesno", weight: 5 },
        { id: "soc_5", question: "Do you have a POSH (Sexual Harassment) committee and policy?", type: "yesno", weight: 5 },
        { id: "soc_6", question: "Do you conduct human rights due diligence in your supply chain?", type: "yesno", weight: 7 },
        { id: "soc_7", question: "CSR spend as % of PAT (last FY)?", type: "percentage", weight: 5 },
      ],
    },
    {
      id: "governance",
      title: "Governance",
      description: "Ethics, transparency, and compliance practices",
      questions: [
        { id: "gov_1", question: "Do you have an anti-bribery/anti-corruption policy?", type: "yesno", weight: 8 },
        { id: "gov_2", question: "Is there a whistleblower mechanism in place?", type: "yesno", weight: 7 },
        { id: "gov_3", question: "Do you publish a sustainability/ESG report?", type: "yesno", weight: 5 },
        { id: "gov_4", question: "Has the company faced any regulatory penalties in last 3 years?", type: "yesno_inverse", weight: 8 },
        { id: "gov_5", question: "Do you have a Board-level ESG/Sustainability committee?", type: "yesno", weight: 5 },
        { id: "gov_6", question: "Is there a data privacy/DPDP compliance framework?", type: "yesno", weight: 5 },
      ],
    },
  ],
};

function calculateScores(responses: Record<string, unknown>): { environment: number; social: number; governance: number; overall: number } {
  let envScore = 0, envMax = 0;
  let socScore = 0, socMax = 0;
  let govScore = 0, govMax = 0;

  for (const section of ESG_QUESTIONNAIRE.sections) {
    for (const q of section.questions) {
      const answer = responses[q.id];
      const weight = q.weight;

      let score = 0;
      if (q.type === "yesno") {
        score = answer === true || answer === "yes" ? weight : 0;
      } else if (q.type === "yesno_inverse") {
        score = answer === false || answer === "no" ? weight : 0;
      } else if (q.type === "percentage") {
        const val = Number(answer) || 0;
        score = (Math.min(val, 100) / 100) * weight;
      } else if (q.type === "number") {
        // For number types, we give partial credit (normalize 0-weight)
        score = answer !== null && answer !== undefined && answer !== "" ? weight * 0.5 : 0;
      }

      if (section.id === "environment") { envScore += score; envMax += weight; }
      else if (section.id === "social") { socScore += score; socMax += weight; }
      else { govScore += score; govMax += weight; }
    }
  }

  const env = envMax > 0 ? (envScore / envMax) * 100 : 0;
  const soc = socMax > 0 ? (socScore / socMax) * 100 : 0;
  const gov = govMax > 0 ? (govScore / govMax) * 100 : 0;
  const overall = (env * 0.4 + soc * 0.35 + gov * 0.25); // weighted

  return {
    environment: Math.round(env * 100) / 100,
    social: Math.round(soc * 100) / 100,
    governance: Math.round(gov * 100) / 100,
    overall: Math.round(overall * 100) / 100,
  };
}
