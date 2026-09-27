# RFC 0004 — Extraction flywheel (correction-driven quality loop)

- Status: **Accepted** (Phase 1+2 landed; monthly cadence below)
- Date: 2026-09-27
- Principle: review-first automation (nothing files without a human)
- Author: Founding engineer

## Summary

Every review Confirm writes the pipeline's proposal (`ai_value`,
`ai_confidence`) onto the entry (migration v37). Any later edit shows up
as drift. `GET /extract/mining` aggregates drift per datapoint with
confidence calibration (avg confidence of drifted vs clean), so pattern
work starts where the model is both wrong and confident.

The deterministic CI gate is `test_field_map_every_id_has_esrs_ref`
every bridge field resolves to a real ESRS datapoint — plus the VSME
`maps_to` resolution test. These catch dead mappings on every push.

## Monthly cadence

1. **Mine.** Call `GET /extract/mining` (per FY, org-wide for owned orgs;
   guest sandboxes excluded by design). Take the top-5 drifted datapoints
   with `avg_conf_drifted >= avg_conf_clean` (confident-but-wrong).
2. **Pattern.** For each: pull 3-5 source snippets (review UI shows them
   per candidate), write/extend a regex or table pattern in
   `app/extraction*.py`, or extend `FIELD_TO_BRSR` in `app/esrs_extract.py`.
3. **Eval.** Run the heavyweight harness locally before shipping:
   `python -m app.eval_cli --pdf-dir <sample-reports> --top-failures 10`
   Compare precision/recall/F1 per field against the last recorded run
   (gold labels in `app/eval_gold.py`, silver in `app/eval_silver.py`).
   Ship only on no-regression.
4. **Ship + record.** Commit pattern + updated gold/silver labels; note the
   F1 delta in the commit message.

## What the loop deliberately does NOT do

- No silent auto-retraining on user data (corrections stay org-scoped;
  only aggregate miss-patterns inform shared patterns).
- No guest-sandbox data in the loop (sandbox rows carry no user identity;
  mining org-wide queries skip them by construction).
- No filing without review: `source="ai-extract"` entries are review
  artifacts until a human confirms them into `reported` status.
