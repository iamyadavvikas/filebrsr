"""
Advanced Platform API Router — Supply Chain, Documents, Workflows, Frameworks,
XBRL Filing, Regulatory Compliance, ESG Ratings, Stakeholder Surveys.
"""

from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
import json
import uuid

from app.config import get_settings

router = APIRouter(prefix="/api/platform", tags=["Advanced Platform"])
settings = get_settings()


def get_supabase_admin():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def get_user_id(authorization: str) -> str:
    """Extract user_id from JWT. Simplified for now."""
    token = authorization.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    # Decode Supabase JWT to get user_id
    try:
        import jwt as pyjwt
        payload = pyjwt.decode(token, options={"verify_signature": False})
        return payload.get("sub", token)
    except Exception:
        return token


# ═══════════════════════════════════════════════════════════════
# SUPPLY CHAIN APIs
# ═══════════════════════════════════════════════════════════════

class SupplierCreate(BaseModel):
    name: str
    category: str = "tier_1"
    industry: Optional[str] = None
    location_state: Optional[str] = None
    annual_spend_inr: Optional[float] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    esg_score: Optional[float] = None
    risk_level: Optional[str] = "medium"


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    industry: Optional[str] = None
    location_state: Optional[str] = None
    annual_spend_inr: Optional[float] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    esg_score: Optional[float] = None
    risk_level: Optional[str] = None
    status: Optional[str] = None


class AssessmentCreate(BaseModel):
    supplier_id: str
    financial_year: str
    assessment_type: str = "questionnaire"
    environment_score: Optional[float] = None
    social_score: Optional[float] = None
    governance_score: Optional[float] = None
    overall_score: Optional[float] = None
    responses: Optional[dict] = None
    findings: Optional[str] = None
    corrective_actions: Optional[str] = None


@router.get("/suppliers")
async def list_suppliers(
    risk_level: Optional[str] = None,
    category: Optional[str] = None,
    authorization: str = Header(...)
):
    """List all suppliers with optional filtering."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    query = supabase.table("suppliers").select("*").eq("user_id", user_id)
    if risk_level:
        query = query.eq("risk_level", risk_level)
    if category:
        query = query.eq("category", category)

    result = query.order("name").execute()
    return {"suppliers": result.data or [], "count": len(result.data or [])}


@router.post("/suppliers")
async def create_supplier(req: SupplierCreate, authorization: str = Header(...)):
    """Add a new supplier."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    data = req.model_dump(exclude_none=True)
    data["user_id"] = user_id

    result = supabase.table("suppliers").insert(data).execute()
    return {"status": "created", "supplier": result.data[0] if result.data else None}


@router.put("/suppliers/{supplier_id}")
async def update_supplier(supplier_id: str, req: SupplierUpdate, authorization: str = Header(...)):
    """Update a supplier."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    data = req.model_dump(exclude_none=True)
    result = supabase.table("suppliers").update(data).eq("id", supplier_id).eq("user_id", user_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"status": "updated", "supplier": result.data[0]}


@router.delete("/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: str, authorization: str = Header(...)):
    """Delete a supplier."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    supabase.table("suppliers").delete().eq("id", supplier_id).eq("user_id", user_id).execute()
    return {"status": "deleted"}


@router.get("/suppliers/{supplier_id}/assessments")
async def list_assessments(supplier_id: str, authorization: str = Header(...)):
    """Get all assessments for a supplier."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    result = supabase.table("supplier_assessments").select("*").eq(
        "supplier_id", supplier_id
    ).eq("user_id", user_id).order("assessed_at", desc=True).execute()

    return {"assessments": result.data or []}


@router.post("/suppliers/assessments")
async def create_assessment(req: AssessmentCreate, authorization: str = Header(...)):
    """Create a supplier ESG assessment."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    data = req.model_dump(exclude_none=True)
    data["user_id"] = user_id
    if req.responses:
        data["responses"] = json.dumps(req.responses)

    # Calculate overall if not provided
    scores = [s for s in [req.environment_score, req.social_score, req.governance_score] if s is not None]
    if scores and not req.overall_score:
        data["overall_score"] = round(sum(scores) / len(scores), 2)

    result = supabase.table("supplier_assessments").insert(data).execute()

    # Update supplier's esg_score and last_assessed_at
    if result.data:
        overall = data.get("overall_score", result.data[0].get("overall_score"))
        if overall:
            supabase.table("suppliers").update({
                "esg_score": overall,
                "last_assessed_at": datetime.utcnow().isoformat()
            }).eq("id", req.supplier_id).execute()

    return {"status": "created", "assessment": result.data[0] if result.data else None}


# ═══════════════════════════════════════════════════════════════
# DOCUMENT EVIDENCE LIBRARY APIs
# ═══════════════════════════════════════════════════════════════

class DocumentCreate(BaseModel):
    file_name: str
    file_url: str
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    category: str = "other"
    description: Optional[str] = None
    financial_year: Optional[str] = None
    linked_datapoints: Optional[List[str]] = None
    linked_principles: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    expiry_date: Optional[str] = None


class DocumentUpdate(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None
    linked_datapoints: Optional[List[str]] = None
    linked_principles: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    verified: Optional[bool] = None
    expiry_date: Optional[str] = None


@router.get("/documents")
async def list_documents(
    category: Optional[str] = None,
    financial_year: Optional[str] = None,
    principle: Optional[str] = None,
    authorization: str = Header(...)
):
    """List all documents with optional filtering."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    query = supabase.table("documents").select("*").eq("user_id", user_id)
    if category:
        query = query.eq("category", category)
    if financial_year:
        query = query.eq("financial_year", financial_year)
    if principle:
        query = query.contains("linked_principles", [principle])

    result = query.order("created_at", desc=True).execute()
    return {"documents": result.data or [], "count": len(result.data or [])}


@router.post("/documents")
async def create_document(req: DocumentCreate, authorization: str = Header(...)):
    """Register a document in the evidence library."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    data = req.model_dump(exclude_none=True)
    data["user_id"] = user_id

    result = supabase.table("documents").insert(data).execute()
    return {"status": "created", "document": result.data[0] if result.data else None}


@router.put("/documents/{doc_id}")
async def update_document(doc_id: str, req: DocumentUpdate, authorization: str = Header(...)):
    """Update document metadata."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    data = req.model_dump(exclude_none=True)
    result = supabase.table("documents").update(data).eq("id", doc_id).eq("user_id", user_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "updated", "document": result.data[0]}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, authorization: str = Header(...)):
    """Delete a document record."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    supabase.table("documents").delete().eq("id", doc_id).eq("user_id", user_id).execute()
    return {"status": "deleted"}


@router.post("/documents/{doc_id}/verify")
async def verify_document(doc_id: str, authorization: str = Header(...)):
    """Mark a document as verified."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    result = supabase.table("documents").update({
        "verified": True,
        "verified_by": user_id,
        "verified_at": datetime.utcnow().isoformat()
    }).eq("id", doc_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "verified", "document": result.data[0]}


# ═══════════════════════════════════════════════════════════════
# WORKFLOW APPROVALS APIs
# ═══════════════════════════════════════════════════════════════

class WorkflowTemplateCreate(BaseModel):
    name: str
    entity_type: str  # 'brsr_entry', 'report', 'action_plan', 'carbon_entry'
    steps: List[dict]  # [{role, approver_id}]


class WorkflowAction(BaseModel):
    action: str  # 'approve', 'reject', 'comment'
    comment: Optional[str] = None


@router.get("/workflows/templates")
async def list_workflow_templates(authorization: str = Header(...)):
    """List all workflow templates."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    result = supabase.table("workflow_templates").select("*").eq("user_id", user_id).execute()
    return {"templates": result.data or []}


@router.post("/workflows/templates")
async def create_workflow_template(req: WorkflowTemplateCreate, authorization: str = Header(...)):
    """Create a workflow template."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    data = {
        "user_id": user_id,
        "name": req.name,
        "entity_type": req.entity_type,
        "steps": json.dumps(req.steps),
    }
    result = supabase.table("workflow_templates").insert(data).execute()
    return {"status": "created", "template": result.data[0] if result.data else None}


@router.post("/workflows/initiate")
async def initiate_workflow(
    template_id: str = Form(...),
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    authorization: str = Header(...)
):
    """Start a workflow instance for an entity."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    data = {
        "template_id": template_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "initiated_by": user_id,
        "current_step": 0,
        "status": "pending",
        "comments": json.dumps([]),
    }
    result = supabase.table("workflow_instances").insert(data).execute()
    return {"status": "initiated", "workflow": result.data[0] if result.data else None}


@router.get("/workflows/instances")
async def list_workflow_instances(
    status: Optional[str] = None,
    entity_type: Optional[str] = None,
    authorization: str = Header(...)
):
    """List workflow instances."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    query = supabase.table("workflow_instances").select("*").eq("initiated_by", user_id)
    if status:
        query = query.eq("status", status)
    if entity_type:
        query = query.eq("entity_type", entity_type)

    result = query.order("created_at", desc=True).execute()
    return {"instances": result.data or []}


@router.post("/workflows/instances/{instance_id}/action")
async def workflow_action(instance_id: str, req: WorkflowAction, authorization: str = Header(...)):
    """Approve, reject, or comment on a workflow step."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    # Get current instance
    instance_result = supabase.table("workflow_instances").select("*").eq("id", instance_id).execute()
    if not instance_result.data:
        raise HTTPException(status_code=404, detail="Workflow instance not found")

    instance = instance_result.data[0]
    comments = json.loads(instance.get("comments", "[]")) if isinstance(instance.get("comments"), str) else (instance.get("comments") or [])

    comments.append({
        "user_id": user_id,
        "action": req.action,
        "comment": req.comment,
        "timestamp": datetime.utcnow().isoformat(),
    })

    update_data = {"comments": json.dumps(comments)}

    if req.action == "approve":
        # Get template to check if there are more steps
        template_result = supabase.table("workflow_templates").select("steps").eq("id", instance["template_id"]).execute()
        total_steps = len(json.loads(template_result.data[0]["steps"])) if template_result.data else 1

        if instance["current_step"] + 1 >= total_steps:
            update_data["status"] = "approved"
        else:
            update_data["current_step"] = instance["current_step"] + 1
            update_data["status"] = "in_review"
    elif req.action == "reject":
        update_data["status"] = "rejected"

    result = supabase.table("workflow_instances").update(update_data).eq("id", instance_id).execute()
    return {"status": req.action, "workflow": result.data[0] if result.data else None}


# ═══════════════════════════════════════════════════════════════
# MULTI-FRAMEWORK MAPPING APIs
# ═══════════════════════════════════════════════════════════════

@router.get("/frameworks/mappings")
async def get_framework_mappings(
    framework: Optional[str] = None,
    brsr_datapoint: Optional[str] = None,
    authorization: str = Header(...)
):
    """Get cross-framework mappings (GRI, CDP, TCFD, SASB, UNGC, SDG)."""
    supabase = get_supabase_admin()

    query = supabase.table("framework_mappings").select("*")
    if framework:
        query = query.eq("framework", framework)
    if brsr_datapoint:
        query = query.eq("brsr_datapoint_id", brsr_datapoint)

    result = query.order("brsr_datapoint_id").execute()

    # Group by framework for stats
    frameworks = {}
    for m in (result.data or []):
        fw = m["framework"]
        if fw not in frameworks:
            frameworks[fw] = {"count": 0, "mappings": []}
        frameworks[fw]["count"] += 1
        frameworks[fw]["mappings"].append(m)

    return {
        "mappings": result.data or [],
        "total": len(result.data or []),
        "by_framework": {k: v["count"] for k, v in frameworks.items()},
    }


@router.get("/frameworks/coverage")
async def get_framework_coverage(
    financial_year: str = "FY2024-25",
    authorization: str = Header(...)
):
    """Get framework coverage based on filled data points."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    # Get user's filled entries
    entries_result = supabase.table("brsr_entries").select("datapoint_id").eq(
        "financial_year", financial_year
    ).execute()
    filled_ids = {e["datapoint_id"] for e in (entries_result.data or [])}

    # Get all mappings
    mappings_result = supabase.table("framework_mappings").select("*").execute()

    # Calculate coverage per framework
    coverage = {}
    for m in (mappings_result.data or []):
        fw = m["framework"]
        if fw not in coverage:
            coverage[fw] = {"total": 0, "covered": 0}
        coverage[fw]["total"] += 1
        if m["brsr_datapoint_id"] in filled_ids:
            coverage[fw]["covered"] += 1

    for fw in coverage:
        c = coverage[fw]
        c["percent"] = round((c["covered"] / c["total"]) * 100, 1) if c["total"] > 0 else 0

    return {"financial_year": financial_year, "coverage": coverage}


# ═══════════════════════════════════════════════════════════════
# XBRL FILING APIs
# ═══════════════════════════════════════════════════════════════

class XBRLFilingCreate(BaseModel):
    financial_year: str
    filing_type: str = "brsr_annual"
    exchange: str = "both"


@router.get("/xbrl/filings")
async def list_xbrl_filings(authorization: str = Header(...)):
    """List all XBRL filings."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    result = supabase.table("xbrl_filings").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return {"filings": result.data or []}


@router.post("/xbrl/generate")
async def generate_xbrl(req: XBRLFilingCreate, authorization: str = Header(...)):
    """Generate XBRL filing from BRSR data."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    # Fetch user's BRSR entries for the financial year
    entries_result = supabase.table("brsr_entries").select("*").eq(
        "financial_year", req.financial_year
    ).execute()

    entries = entries_result.data or []
    if not entries:
        raise HTTPException(status_code=400, detail="No BRSR data found for this financial year. Fill data first.")

    # Generate XBRL XML
    xbrl_content = _generate_xbrl_xml(entries, req.financial_year, req.exchange)

    # Validate
    validation_errors = _validate_xbrl(xbrl_content, entries)
    validation_status = "validated" if not validation_errors else "errors"

    # Save filing
    data = {
        "user_id": user_id,
        "financial_year": req.financial_year,
        "filing_type": req.filing_type,
        "exchange": req.exchange,
        "xbrl_content": xbrl_content,
        "validation_status": validation_status,
        "validation_errors": json.dumps(validation_errors) if validation_errors else None,
    }
    result = supabase.table("xbrl_filings").insert(data).execute()

    return {
        "status": "generated",
        "validation_status": validation_status,
        "errors_count": len(validation_errors),
        "filing": result.data[0] if result.data else None,
    }


@router.get("/xbrl/filings/{filing_id}/download")
async def download_xbrl(filing_id: str, authorization: str = Header(...)):
    """Download XBRL XML content."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    result = supabase.table("xbrl_filings").select("xbrl_content, financial_year, exchange").eq(
        "id", filing_id
    ).eq("user_id", user_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Filing not found")

    from fastapi.responses import Response
    filing = result.data[0]
    filename = f"BRSR_{filing['financial_year']}_{filing['exchange']}.xml"

    return Response(
        content=filing["xbrl_content"],
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _generate_xbrl_xml(entries: list, financial_year: str, exchange: str) -> str:
    """Generate BRSR XBRL XML from entries."""
    # Map datapoint_ids to XBRL tags (BSE/NSE taxonomy)
    XBRL_TAG_MAP = {
        "A.I.1": "in-brsr:CINOfEntity",
        "A.I.2": "in-brsr:NameOfEntity",
        "A.I.3": "in-brsr:YearOfIncorporation",
        "A.I.4": "in-brsr:RegisteredOfficeAddress",
        "A.I.5": "in-brsr:CorporateOfficeAddress",
        "A.I.6": "in-brsr:EmailAddress",
        "A.I.7": "in-brsr:TelephoneNumber",
        "A.I.8": "in-brsr:WebsiteURL",
        "A.I.9": "in-brsr:ReportingPeriod",
        "A.II.1": "in-brsr:PaidUpCapital",
        "A.II.2": "in-brsr:TotalTurnover",
        "C.P6.GHG.1": "in-brsr:TotalScopeOneEmissions",
        "C.P6.GHG.2": "in-brsr:TotalScopeTwoEmissions",
        "C.P6.GHG.3": "in-brsr:TotalScopeThreeEmissions",
        "C.P6.Energy.1": "in-brsr:TotalEnergyConsumption",
        "C.P6.Energy.2": "in-brsr:EnergyIntensityRatio",
        "C.P6.Water.1": "in-brsr:TotalWaterWithdrawal",
        "C.P6.Water.2": "in-brsr:TotalWaterConsumption",
        "C.P6.Waste.1": "in-brsr:TotalWasteGenerated",
        "C.P3.Emp.1": "in-brsr:TotalEmployees",
        "C.P3.Safety.1": "in-brsr:SafetyIncidents",
        "C.P3.Training.1": "in-brsr:AverageTrainingHours",
    }

    # Build entry map
    entry_map = {}
    for e in entries:
        entry_map[e["datapoint_id"]] = e.get("value", "")

    # Generate XML
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"',
        '  xmlns:in-brsr="http://www.sebi.gov.in/xbrl/brsr/2024"',
        '  xmlns:xlink="http://www.w3.org/1999/xlink"',
        '  xmlns:iso4217="http://www.xbrl.org/2003/iso4217">',
        '',
        f'  <!-- BRSR Filing: {financial_year} | Exchange: {exchange.upper()} -->',
        f'  <xbrli:context id="ctx_{financial_year}">',
        '    <xbrli:entity>',
        f'      <xbrli:identifier scheme="http://www.sebi.gov.in">{entry_map.get("A.I.1", "")}</xbrli:identifier>',
        '    </xbrli:entity>',
        '    <xbrli:period>',
        f'      <xbrli:instant>{financial_year}</xbrli:instant>',
        '    </xbrli:period>',
        '  </xbrli:context>',
        '',
    ]

    for dp_id, xbrl_tag in XBRL_TAG_MAP.items():
        value = entry_map.get(dp_id, "")
        if value:
            # Clean JSON-wrapped values
            if isinstance(value, str) and value.startswith('"'):
                try:
                    value = json.loads(value)
                except Exception:
                    pass
            lines.append(f'  <{xbrl_tag} contextRef="ctx_{financial_year}">{value}</{xbrl_tag}>')

    lines.append('')
    lines.append('</xbrli:xbrl>')
    return '\n'.join(lines)


def _validate_xbrl(xbrl_content: str, entries: list) -> list:
    """Validate XBRL completeness."""
    errors = []
    required_fields = ["A.I.1", "A.I.2", "A.II.2", "C.P6.GHG.1", "C.P6.Energy.1"]
    filled_ids = {e["datapoint_id"] for e in entries}

    for field in required_fields:
        if field not in filled_ids:
            errors.append({"field": field, "error": f"Required field {field} is missing"})

    return errors


# ═══════════════════════════════════════════════════════════════
# REGULATORY COMPLIANCE APIs
# ═══════════════════════════════════════════════════════════════

class ComplianceCreate(BaseModel):
    regulation: str
    financial_year: str
    status: str = "not_started"
    compliance_data: Optional[dict] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None


class ComplianceUpdate(BaseModel):
    status: Optional[str] = None
    compliance_data: Optional[dict] = None
    filed_date: Optional[str] = None
    filing_reference: Optional[str] = None
    notes: Optional[str] = None


@router.get("/compliance")
async def list_compliance(
    financial_year: Optional[str] = None,
    regulation: Optional[str] = None,
    authorization: str = Header(...)
):
    """List regulatory compliance records."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    query = supabase.table("regulatory_compliance").select("*").eq("user_id", user_id)
    if financial_year:
        query = query.eq("financial_year", financial_year)
    if regulation:
        query = query.eq("regulation", regulation)

    result = query.order("regulation").execute()
    return {"compliance": result.data or [], "count": len(result.data or [])}


@router.post("/compliance")
async def create_compliance(req: ComplianceCreate, authorization: str = Header(...)):
    """Create or update a compliance record."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    data = req.model_dump(exclude_none=True)
    data["user_id"] = user_id
    if req.compliance_data:
        data["compliance_data"] = json.dumps(req.compliance_data)

    result = supabase.table("regulatory_compliance").insert(data).execute()
    return {"status": "created", "compliance": result.data[0] if result.data else None}


@router.put("/compliance/{compliance_id}")
async def update_compliance(compliance_id: str, req: ComplianceUpdate, authorization: str = Header(...)):
    """Update a compliance record."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    data = req.model_dump(exclude_none=True)
    if "compliance_data" in data:
        data["compliance_data"] = json.dumps(data["compliance_data"])

    result = supabase.table("regulatory_compliance").update(data).eq("id", compliance_id).eq("user_id", user_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Compliance record not found")
    return {"status": "updated", "compliance": result.data[0]}


# ═══════════════════════════════════════════════════════════════
# ESG RATINGS APIs
# ═══════════════════════════════════════════════════════════════

class ESGRatingCreate(BaseModel):
    agency: str
    financial_year: str
    current_rating: Optional[str] = None
    target_rating: Optional[str] = None
    readiness_score: Optional[float] = None
    gap_areas: Optional[List[dict]] = None


class ESGRatingUpdate(BaseModel):
    current_rating: Optional[str] = None
    target_rating: Optional[str] = None
    readiness_score: Optional[float] = None
    gap_areas: Optional[List[dict]] = None


@router.get("/esg-ratings")
async def list_esg_ratings(
    financial_year: Optional[str] = None,
    agency: Optional[str] = None,
    authorization: str = Header(...)
):
    """List ESG rating readiness assessments."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    query = supabase.table("esg_ratings").select("*").eq("user_id", user_id)
    if financial_year:
        query = query.eq("financial_year", financial_year)
    if agency:
        query = query.eq("agency", agency)

    result = query.order("agency").execute()
    return {"ratings": result.data or []}


@router.post("/esg-ratings")
async def create_esg_rating(req: ESGRatingCreate, authorization: str = Header(...)):
    """Create an ESG rating assessment."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    data = req.model_dump(exclude_none=True)
    data["user_id"] = user_id
    if req.gap_areas:
        data["gap_areas"] = json.dumps(req.gap_areas)

    result = supabase.table("esg_ratings").insert(data).execute()
    return {"status": "created", "rating": result.data[0] if result.data else None}


@router.put("/esg-ratings/{rating_id}")
async def update_esg_rating(rating_id: str, req: ESGRatingUpdate, authorization: str = Header(...)):
    """Update an ESG rating assessment."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    data = req.model_dump(exclude_none=True)
    if "gap_areas" in data:
        data["gap_areas"] = json.dumps(data["gap_areas"])
    data["last_assessed_at"] = datetime.utcnow().isoformat()

    result = supabase.table("esg_ratings").update(data).eq("id", rating_id).eq("user_id", user_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Rating not found")
    return {"status": "updated", "rating": result.data[0]}


# ═══════════════════════════════════════════════════════════════
# STAKEHOLDER SURVEYS APIs
# ═══════════════════════════════════════════════════════════════

class SurveyCreate(BaseModel):
    title: str
    stakeholder_type: str
    questions: List[dict]  # [{id, question, type, options}]
    closes_at: Optional[str] = None


@router.get("/surveys")
async def list_surveys(authorization: str = Header(...)):
    """List all stakeholder surveys."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    result = supabase.table("stakeholder_surveys").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return {"surveys": result.data or []}


@router.post("/surveys")
async def create_survey(req: SurveyCreate, authorization: str = Header(...)):
    """Create a stakeholder survey."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    share_link = f"survey_{uuid.uuid4().hex[:8]}"
    data = {
        "user_id": user_id,
        "title": req.title,
        "stakeholder_type": req.stakeholder_type,
        "questions": json.dumps(req.questions),
        "share_link": share_link,
        "status": "draft",
    }
    if req.closes_at:
        data["closes_at"] = req.closes_at

    result = supabase.table("stakeholder_surveys").insert(data).execute()
    return {"status": "created", "survey": result.data[0] if result.data else None, "share_link": share_link}


@router.put("/surveys/{survey_id}/publish")
async def publish_survey(survey_id: str, authorization: str = Header(...)):
    """Publish a survey (make it active)."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    result = supabase.table("stakeholder_surveys").update({"status": "active"}).eq(
        "id", survey_id
    ).eq("user_id", user_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Survey not found")
    return {"status": "published", "survey": result.data[0]}


@router.put("/surveys/{survey_id}/close")
async def close_survey(survey_id: str, authorization: str = Header(...)):
    """Close a survey."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    result = supabase.table("stakeholder_surveys").update({"status": "closed"}).eq(
        "id", survey_id
    ).eq("user_id", user_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Survey not found")
    return {"status": "closed", "survey": result.data[0]}


# ═══════════════════════════════════════════════════════════════
# MATERIALITY ASSESSMENT APIs
# ═══════════════════════════════════════════════════════════════

class MaterialityTopicUpdate(BaseModel):
    topic_id: str
    impact_score: float  # 1-10
    financial_score: float  # 1-10
    stakeholder_relevance: Optional[str] = None


@router.get("/materiality")
async def get_materiality_topics(
    financial_year: str = "FY2024-25",
    authorization: str = Header(...)
):
    """Get materiality assessment topics."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    result = supabase.table("materiality_topics").select("*").eq(
        "user_id", user_id
    ).eq("financial_year", financial_year).execute()

    return {"topics": result.data or [], "financial_year": financial_year}


@router.post("/materiality")
async def save_materiality_topics(
    financial_year: str = Form("FY2024-25"),
    topics: str = Form(...),  # JSON array of topics
    authorization: str = Header(...)
):
    """Save materiality assessment topics (bulk upsert)."""
    user_id = await get_user_id(authorization)
    supabase = get_supabase_admin()

    topics_data = json.loads(topics)
    saved = 0

    for topic in topics_data:
        data = {
            "user_id": user_id,
            "financial_year": financial_year,
            "topic_name": topic.get("name", ""),
            "category": topic.get("category", "environmental"),
            "impact_score": topic.get("impact_score", 5),
            "financial_score": topic.get("financial_score", 5),
            "stakeholder_relevance": topic.get("stakeholder_relevance"),
        }
        supabase.table("materiality_topics").upsert(data, on_conflict="user_id,financial_year,topic_name").execute()
        saved += 1

    return {"status": "saved", "count": saved}
