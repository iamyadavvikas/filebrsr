"""
Background Extraction Worker
==============================
Polls `extraction_jobs` table for queued jobs and processes them.
Runs as a separate process alongside the main API.

Usage:
  python -m app.worker
"""

import asyncio
import time
import logging
import io
import pdfplumber
from datetime import datetime

from app.config import get_settings
from app.extraction import extract_with_regex, calculate_confidence
from app.extraction_enhanced import extract_enhanced
from app.ai_extraction import extract_with_ai
from app.agent_extraction import extract_with_agent
from app.nifty50_benchmarks import get_benchmark_comparison
from app.brsr_datapoints import get_datapoints_stats, analyze_gaps_v2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [worker] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("worker")

settings = get_settings()

POLL_INTERVAL = 3  # seconds
MAX_CONCURRENT = 2  # max parallel extractions


def get_supabase():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def process_job(job: dict) -> None:
    """Process a single extraction job."""
    sb = get_supabase()
    job_id = job["id"]
    report_id = job["report_id"]
    file_url = job["file_url"]

    logger.info("Processing job %s (report: %s)", job_id, report_id)

    # Mark as processing
    sb.table("extraction_jobs").update({
        "status": "processing",
        "started_at": datetime.utcnow().isoformat(),
    }).eq("id", job_id).execute()

    try:
        # Download file from Supabase Storage
        file_bytes = sb.storage.from_("brsr-reports").download(file_url)
        if not file_bytes:
            raise Exception("Could not download file from storage")

        # Extract text from PDF (limit 80 pages)
        text = ""
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= 80:
                    break
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            raise Exception("No text could be extracted from PDF")

        # Triple extraction: regex + enhanced + AI
        regex_results = extract_with_regex(text)
        enhanced_results = extract_enhanced(text)

        # AI extraction with fallback chain: Gemini → Groq Agent → single-shot
        ai_results = {"section_a": {}, "section_b": {}, "section_c": {}}
        try:
            # Try multi-pass agent first (Groq)
            ai_results = await extract_with_agent(text, settings.GROQ_API_KEY)
            agent_fields = sum(len(v) for v in ai_results.values() if isinstance(v, dict))
            if agent_fields < 10:
                # Supplement with single-shot
                single_shot = await extract_with_ai(
                    text, settings.GEMINI_API_KEY, settings.GROQ_API_KEY, settings.ANTHROPIC_API_KEY
                )
                for section in ["section_a", "section_b", "section_c"]:
                    for k, v in single_shot.get(section, {}).items():
                        if k not in ai_results.get(section, {}):
                            ai_results.setdefault(section, {})[k] = v
        except Exception as e:
            logger.warning("Agent extraction failed, trying single-shot: %s", e)
            try:
                ai_results = await extract_with_ai(
                    text, settings.GEMINI_API_KEY, settings.GROQ_API_KEY, settings.ANTHROPIC_API_KEY
                )
            except Exception as e2:
                logger.error("All AI extraction failed: %s", e2)

        # Merge: enhanced base → regex fills → AI takes precedence
        merged = {"section_a": {}, "section_b": {}, "section_c": {}}
        for section in ["section_a", "section_b", "section_c"]:
            merged[section] = {**enhanced_results.get(section, {})}
            merged[section].update(regex_results.get(section, {}))
            merged[section].update(ai_results.get(section, {}))

        confidence = calculate_confidence(regex_results, ai_results)
        company_name = merged.get("section_a", {}).get("company_name", None)
        financial_year = merged.get("section_a", {}).get("financial_year", None)
        benchmark = get_benchmark_comparison(merged)
        gap_analysis = analyze_gaps_v2(merged)
        datapoints_stats = get_datapoints_stats()

        full_extracted = {
            **merged,
            "gap_analysis": gap_analysis,
            "datapoints_stats": datapoints_stats,
            "benchmark": benchmark,
        }

        # Update report
        sb.table("reports").update({
            "status": "completed",
            "extracted_data": full_extracted,
            "confidence_scores": confidence,
            "company_name": company_name,
            "financial_year": financial_year,
        }).eq("id", report_id).execute()

        # Mark job complete
        sb.table("extraction_jobs").update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", job_id).execute()

        logger.info("Job %s completed successfully", job_id)

    except Exception as e:
        logger.error("Job %s failed: %s", job_id, str(e))
        sb.table("reports").update({"status": "failed"}).eq("id", report_id).execute()
        sb.table("extraction_jobs").update({
            "status": "failed",
            "error": str(e)[:500],
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", job_id).execute()


async def worker_loop():
    """Main worker loop — polls for queued jobs."""
    logger.info("Worker started. Polling every %ds for queued jobs...", POLL_INTERVAL)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    while True:
        try:
            sb = get_supabase()
            # Fetch queued jobs (oldest first)
            result = sb.table("extraction_jobs").select("*").eq(
                "status", "queued"
            ).order("created_at").limit(MAX_CONCURRENT).execute()

            jobs = result.data or []

            if jobs:
                logger.info("Found %d queued job(s)", len(jobs))
                tasks = []
                for job in jobs:
                    async def _run(j=job):
                        async with semaphore:
                            await process_job(j)
                    tasks.append(asyncio.create_task(_run()))
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error("Worker poll error: %s", e)

        await asyncio.sleep(POLL_INTERVAL)


def main():
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
