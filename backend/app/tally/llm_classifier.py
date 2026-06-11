"""
LLM fallback classifier for HSN/SAC → GHG scope mapping.

When :func:`app.tally.classifier.classify_hsn` returns ``unmapped`` (HSN
not in the seed JSON, or no HSN on the voucher at all — only ``narration``
+ ``ledger_name``), we optionally consult an LLM. The LLM sees the
narration / vendor / ledger free-text and returns a structured
classification.

Backends today:
  * **Sarvam-M** — best for Hindi / Hinglish narrations that smaller
    Indian SMEs write in their Tally vouchers
  * **OpenAI gpt-4o-mini** — better for English narrations and obscure
    HSN descriptions
  * **MockClassifier** — canned response, used in CI and unit tests
  * **DisabledClassifier** — returns ``None``; chosen when no key is set
    so the system stays deterministic in dev environments

Backend selection is driven by env ``LLM_CLASSIFIER_BACKEND`` (one of
``sarvam`` / ``openai`` / ``mock`` / ``disabled``) and the relevant API
key env (``SARVAM_API_KEY`` / ``OPENAI_API_KEY``). The factory caches the
chosen backend per-process; tests call :func:`reset_classifier_cache`.

**Confidence policy**: LLM-classified rows are stamped
``confidence == "medium"``. ``"high"`` is reserved for matches against
the curated JSON seed. This guarantees an analyst can always run
``WHERE classification_confidence = 'high'`` to get the rows that were
classified deterministically, not by a model that may have hallucinated.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


# ─── Result type ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LLMClassification:
    """What an LLM classifier returns. ``None`` means the model couldn't
    confidently classify and we should leave the row as ``unmapped``."""

    scope: int                                 # 1, 2, or 3
    scope3_category: str | None                # required when scope == 3
    emission_basis: str                        # "quantity" | "spend"
    description: str                           # short rationale (logged, not stored)
    suggested_hsn_prefix: str | None           # the model's guess at an HSN seed key
    raw_response: dict[str, Any]               # original parsed JSON for audit


# ─── Interface ───────────────────────────────────────────────────────────


class LLMClassifier(ABC):
    """A classifier that takes free-text Tally fields and returns either
    a structured :class:`LLMClassification` or ``None`` when it can't
    classify confidently."""

    name: str = "abstract"

    @abstractmethod
    def classify(
        self,
        *,
        narration: str | None,
        vendor_name: str | None,
        ledger_name: str | None,
        hsn_code: str | None = None,
    ) -> LLMClassification | None:
        """Return a classification or ``None``. Should never raise on
        normal failure — log + return ``None`` instead so the pipeline
        continues."""


# ─── Disabled / Mock implementations ─────────────────────────────────────


class DisabledClassifier(LLMClassifier):
    """No-op classifier. Selected when no LLM is configured."""

    name = "disabled"

    def classify(self, **_kwargs: Any) -> LLMClassification | None:
        return None


class MockClassifier(LLMClassifier):
    """Returns a canned classification. Tests assert behaviour against
    this so we never need network in CI."""

    name = "mock"

    def __init__(self, response: LLMClassification | None = None) -> None:
        # Default canned response: scope 3 / purchased goods, low-quality
        # spend-basis estimate. Tests can override.
        self.response = response or LLMClassification(
            scope=3,
            scope3_category="purchased_goods_and_services",
            emission_basis="spend",
            description="mock fallback classification",
            suggested_hsn_prefix=None,
            raw_response={"mock": True},
        )

    def classify(self, **_kwargs: Any) -> LLMClassification | None:
        return self.response


# ─── Real implementations (lazy httpx import) ────────────────────────────


_SYSTEM_PROMPT = (
    "You are an expert in Indian accounting (Tally ERP) and GHG Protocol "
    "Scope 1/2/3 categorisation for BRSR Principle 6 reporting. Given a "
    "ledger entry's narration, vendor name, ledger name, and (optional) "
    "HSN code, return a JSON object with the GHG scope and Scope-3 "
    "category. Respond with JSON only — no prose."
)

_RESPONSE_SCHEMA_HINT = (
    'Return JSON exactly matching: '
    '{"scope": 1|2|3, "scope3_category": "<see list>"|null, '
    '"emission_basis": "quantity"|"spend", '
    '"description": "<one sentence reason>", '
    '"suggested_hsn_prefix": "<4-digit HSN if you can guess one>"|null}. '
    "If you cannot classify confidently, return "
    '{"scope": null}. '
    "Valid scope3_category values: purchased_goods_and_services, "
    "capital_goods, fuel_and_energy_related, upstream_transport, "
    "waste_generated, business_travel, employee_commuting, "
    "downstream_transport, processing_of_sold_products, use_of_sold_products, "
    "end_of_life, leased_assets_downstream, franchises, investments."
)


def _build_user_prompt(
    narration: str | None, vendor_name: str | None,
    ledger_name: str | None, hsn_code: str | None,
) -> str:
    parts = [_RESPONSE_SCHEMA_HINT, "", "Ledger entry:"]
    if vendor_name:
        parts.append(f"- Vendor: {vendor_name}")
    if ledger_name:
        parts.append(f"- Ledger: {ledger_name}")
    if narration:
        parts.append(f"- Narration: {narration}")
    if hsn_code:
        parts.append(f"- HSN code (unmapped in our seed): {hsn_code}")
    return "\n".join(parts)


def _parse_llm_json(raw: str) -> LLMClassification | None:
    """LLMs sometimes wrap JSON in ```json ... ``` fences or trailing text.
    Strip the obvious cases, then ``json.loads``. Returns ``None`` on any
    parse / schema failure."""
    body = raw.strip()
    if body.startswith("```"):
        # ```json\n{...}\n```  →  {...}
        body = body.strip("`")
        if body.lower().startswith("json"):
            body = body[4:]
        body = body.strip()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        logger.warning("llm classifier: response was not valid JSON: %s", exc)
        return None

    scope = payload.get("scope")
    if scope is None:
        return None
    if scope not in (1, 2, 3):
        logger.warning("llm classifier: invalid scope %r in response", scope)
        return None

    basis = payload.get("emission_basis", "spend")
    if basis not in ("quantity", "spend"):
        basis = "spend"

    return LLMClassification(
        scope=int(scope),
        scope3_category=payload.get("scope3_category"),
        emission_basis=basis,
        description=str(payload.get("description", "")),
        suggested_hsn_prefix=payload.get("suggested_hsn_prefix"),
        raw_response=payload,
    )


class _HttpJSONClassifier(LLMClassifier):
    """Shared httpx + OpenAI-style chat-completions plumbing for the real
    backends. Subclasses set ``endpoint`` / ``model`` / ``api_key``."""

    name = "http"
    endpoint: str = ""
    model: str = ""
    api_key: str = ""
    timeout_seconds: float = 10.0

    def classify(
        self,
        *,
        narration: str | None,
        vendor_name: str | None,
        ledger_name: str | None,
        hsn_code: str | None = None,
    ) -> LLMClassification | None:
        # All three free-text fields empty → don't waste an API call.
        if not any((narration, vendor_name, ledger_name)):
            return None

        try:
            import httpx  # noqa: PLC0415 — lazy so unit tests don't need httpx mocked
        except ImportError:
            logger.warning("llm classifier: httpx not installed; disabling backend")
            return None

        user_prompt = _build_user_prompt(narration, vendor_name, ledger_name, hsn_code)
        body = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(self.endpoint, json=body, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001 — network / 5xx, keep pipeline alive
            logger.warning("llm classifier %s: request failed: %s", self.name, exc)
            return None

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("llm classifier %s: malformed response: %s", self.name, exc)
            return None
        return _parse_llm_json(content)


class SarvamMClassifier(_HttpJSONClassifier):
    """Sarvam-M via OpenAI-compatible chat endpoint. Pick this for
    Hindi/Hinglish narrations common in tier-2 SME Tally books."""

    name = "sarvam"
    endpoint = "https://api.sarvam.ai/v1/chat/completions"
    model = "sarvam-m"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("SARVAM_API_KEY", "")


class OpenAIMiniClassifier(_HttpJSONClassifier):
    """gpt-4o-mini via OpenAI chat-completions. Better fit for English
    narrations and obscure HSN descriptions."""

    name = "openai"
    endpoint = "https://api.openai.com/v1/chat/completions"
    model = "gpt-4o-mini"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")


# ─── Factory ─────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_llm_classifier() -> LLMClassifier:
    """Resolve the backend once per process, based on env.

    ``LLM_CLASSIFIER_BACKEND`` selects the backend. If the corresponding
    API key env is missing for ``sarvam`` / ``openai`` we degrade to
    ``DisabledClassifier`` (with a log warning) rather than crash at
    request time.
    """
    backend = os.environ.get("LLM_CLASSIFIER_BACKEND", "disabled").strip().lower()
    if backend == "mock":
        return MockClassifier()
    if backend == "sarvam":
        if not os.environ.get("SARVAM_API_KEY"):
            logger.warning("LLM_CLASSIFIER_BACKEND=sarvam but SARVAM_API_KEY is unset; disabling")
            return DisabledClassifier()
        return SarvamMClassifier()
    if backend == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            logger.warning("LLM_CLASSIFIER_BACKEND=openai but OPENAI_API_KEY is unset; disabling")
            return DisabledClassifier()
        return OpenAIMiniClassifier()
    return DisabledClassifier()


def reset_classifier_cache() -> None:
    """Test helper — drop the cached factory result. Defensive against
    monkeypatching: if a test replaced ``get_llm_classifier`` with a plain
    callable, there's nothing to clear and we no-op."""
    clear = getattr(get_llm_classifier, "cache_clear", None)
    if clear is not None:
        clear()
