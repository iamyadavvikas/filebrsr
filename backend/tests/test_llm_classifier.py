"""Tests for the LLM fallback classifier (Slice 2)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.tally.classifier import classify_with_llm_fallback, reset_cache
from app.tally.llm_classifier import (
    DisabledClassifier,
    LLMClassification,
    MockClassifier,
    OpenAIMiniClassifier,
    SarvamMClassifier,
    _build_user_prompt,
    _parse_llm_json,
    get_llm_classifier,
    reset_classifier_cache,
)


@pytest.fixture(autouse=True)
def _reset_caches(monkeypatch):
    """Each test gets a fresh factory + lookup cache. Also strips any
    backend env vars so tests don't accidentally hit live APIs."""
    reset_classifier_cache()
    reset_cache()
    for var in (
        "LLM_CLASSIFIER_BACKEND", "SARVAM_API_KEY", "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    yield
    reset_classifier_cache()
    reset_cache()


# ─── Factory / env wiring ────────────────────────────────────────────────


def test_factory_defaults_to_disabled():
    assert isinstance(get_llm_classifier(), DisabledClassifier)


def test_factory_picks_mock(monkeypatch):
    monkeypatch.setenv("LLM_CLASSIFIER_BACKEND", "mock")
    reset_classifier_cache()
    assert isinstance(get_llm_classifier(), MockClassifier)


def test_factory_picks_sarvam_with_key(monkeypatch):
    monkeypatch.setenv("LLM_CLASSIFIER_BACKEND", "sarvam")
    monkeypatch.setenv("SARVAM_API_KEY", "sk-test")
    reset_classifier_cache()
    classifier = get_llm_classifier()
    assert isinstance(classifier, SarvamMClassifier)
    assert classifier.api_key == "sk-test"


def test_factory_picks_openai_with_key(monkeypatch):
    monkeypatch.setenv("LLM_CLASSIFIER_BACKEND", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    reset_classifier_cache()
    assert isinstance(get_llm_classifier(), OpenAIMiniClassifier)


def test_factory_falls_back_to_disabled_when_key_missing(monkeypatch):
    monkeypatch.setenv("LLM_CLASSIFIER_BACKEND", "sarvam")
    # no SARVAM_API_KEY
    reset_classifier_cache()
    assert isinstance(get_llm_classifier(), DisabledClassifier)


def test_factory_unknown_backend_disabled(monkeypatch):
    monkeypatch.setenv("LLM_CLASSIFIER_BACKEND", "anthropic-claude")
    reset_classifier_cache()
    assert isinstance(get_llm_classifier(), DisabledClassifier)


# ─── MockClassifier ──────────────────────────────────────────────────────


def test_mock_classifier_returns_canned():
    m = MockClassifier()
    result = m.classify(
        narration="diesel for genset", vendor_name="HPCL", ledger_name="Fuel",
    )
    assert result is not None
    assert result.scope == 3
    assert result.emission_basis == "spend"


def test_mock_classifier_accepts_override():
    custom = LLMClassification(
        scope=1, scope3_category=None, emission_basis="quantity",
        description="custom", suggested_hsn_prefix="2710",
        raw_response={},
    )
    m = MockClassifier(response=custom)
    assert m.classify(narration="x", vendor_name=None, ledger_name=None) == custom


def test_disabled_classifier_returns_none():
    assert DisabledClassifier().classify(
        narration="x", vendor_name="y", ledger_name="z",
    ) is None


# ─── _parse_llm_json ─────────────────────────────────────────────────────


def test_parse_llm_json_plain():
    raw = json.dumps({
        "scope": 3, "scope3_category": "purchased_goods_and_services",
        "emission_basis": "spend", "description": "test",
        "suggested_hsn_prefix": "9988",
    })
    result = _parse_llm_json(raw)
    assert result is not None
    assert result.scope == 3
    assert result.scope3_category == "purchased_goods_and_services"


def test_parse_llm_json_fenced():
    raw = '```json\n{"scope": 1, "emission_basis": "quantity", "description": "diesel"}\n```'
    result = _parse_llm_json(raw)
    assert result is not None
    assert result.scope == 1
    assert result.emission_basis == "quantity"


def test_parse_llm_json_returns_none_on_null_scope():
    raw = json.dumps({"scope": None})
    assert _parse_llm_json(raw) is None


def test_parse_llm_json_returns_none_on_invalid_scope():
    assert _parse_llm_json(json.dumps({"scope": 99})) is None


def test_parse_llm_json_returns_none_on_garbage():
    assert _parse_llm_json("this is not json") is None


def test_parse_llm_json_normalises_bad_basis():
    raw = json.dumps({"scope": 2, "emission_basis": "weird"})
    result = _parse_llm_json(raw)
    assert result is not None and result.emission_basis == "spend"


# ─── _build_user_prompt ──────────────────────────────────────────────────


def test_build_user_prompt_includes_all_fields():
    prompt = _build_user_prompt(
        narration="Diesel purchase for backup genset",
        vendor_name="Hindustan Petroleum",
        ledger_name="Fuel & Power",
        hsn_code="27101920",
    )
    assert "Hindustan Petroleum" in prompt
    assert "Fuel & Power" in prompt
    assert "Diesel purchase" in prompt
    assert "27101920" in prompt


def test_build_user_prompt_skips_empty_fields():
    prompt = _build_user_prompt(
        narration=None, vendor_name="ACME", ledger_name=None, hsn_code=None,
    )
    assert "- Vendor: ACME" in prompt
    assert "- Narration:" not in prompt
    assert "- Ledger:" not in prompt


# ─── HTTP backend (mocked httpx) ─────────────────────────────────────────


def _fake_httpx_response(content_json: dict):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(content_json)}}]
    }
    return response


def test_sarvam_classifier_happy_path(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "test")
    classifier = SarvamMClassifier()

    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False
    fake_client.post.return_value = _fake_httpx_response({
        "scope": 3, "scope3_category": "fuel_and_energy_related",
        "emission_basis": "spend", "description": "fuel-related",
    })

    with patch("httpx.Client", return_value=fake_client):
        result = classifier.classify(
            narration="Diesel for genset", vendor_name="HPCL", ledger_name="Fuel",
        )
    assert result is not None
    assert result.scope == 3
    assert result.scope3_category == "fuel_and_energy_related"
    # Verify the POST body shape
    call_kwargs = fake_client.post.call_args.kwargs
    assert call_kwargs["json"]["model"] == "sarvam-m"
    assert call_kwargs["json"]["temperature"] == 0
    assert call_kwargs["headers"]["Authorization"] == "Bearer test"


def test_openai_classifier_happy_path(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-oai")
    classifier = OpenAIMiniClassifier()

    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False
    fake_client.post.return_value = _fake_httpx_response({
        "scope": 2, "scope3_category": None,
        "emission_basis": "quantity", "description": "purchased electricity",
    })

    with patch("httpx.Client", return_value=fake_client):
        result = classifier.classify(
            narration="Electricity bill MSEDCL", vendor_name="MSEDCL", ledger_name="Power",
        )
    assert result is not None
    assert result.scope == 2
    assert classifier.model == "gpt-4o-mini"


def test_http_classifier_returns_none_on_empty_freetext(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    classifier = OpenAIMiniClassifier()
    # No narration / vendor / ledger → should skip the API call entirely
    with patch("httpx.Client") as mock_client:
        result = classifier.classify(narration=None, vendor_name=None, ledger_name=None)
    assert result is None
    mock_client.assert_not_called()


def test_http_classifier_returns_none_on_network_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    classifier = OpenAIMiniClassifier()

    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False
    fake_client.post.side_effect = RuntimeError("DNS failure")

    with patch("httpx.Client", return_value=fake_client):
        result = classifier.classify(narration="test", vendor_name=None, ledger_name=None)
    assert result is None  # quiet failure, not exception


def test_http_classifier_returns_none_on_malformed_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    classifier = OpenAIMiniClassifier()

    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False
    bad_response = MagicMock()
    bad_response.raise_for_status = MagicMock()
    bad_response.json.return_value = {"unexpected": "shape"}
    fake_client.post.return_value = bad_response

    with patch("httpx.Client", return_value=fake_client):
        result = classifier.classify(narration="test", vendor_name=None, ledger_name=None)
    assert result is None


# ─── classify_with_llm_fallback integration ──────────────────────────────


def test_fallback_skipped_when_static_match_succeeds(monkeypatch):
    """HSN 2710 hits the JSON seed → LLM should NOT be consulted."""
    monkeypatch.setenv("LLM_CLASSIFIER_BACKEND", "mock")
    reset_classifier_cache()
    result = classify_with_llm_fallback(
        "27101920", narration="diesel", vendor_name="HPCL", ledger_name="Fuel",
    )
    assert result.confidence == "high"
    # Description came from the JSON seed, not the mock
    assert "mock fallback" not in (result.description or "")


def test_fallback_used_when_static_returns_unmapped(monkeypatch):
    """HSN 99999999 isn't in the seed → MockClassifier should fill in."""
    monkeypatch.setenv("LLM_CLASSIFIER_BACKEND", "mock")
    reset_classifier_cache()
    result = classify_with_llm_fallback(
        "99999999", narration="Annual office party catering",
        vendor_name="Some Caterer", ledger_name="Misc",
    )
    assert result.confidence == "medium"  # never "high" for LLM
    assert result.scope == 3
    assert result.description == "mock fallback classification"
    assert result.version.endswith("+llm:mock")


def test_fallback_returns_unmapped_when_no_hsn_and_disabled():
    """No HSN + disabled backend → stays unmapped."""
    result = classify_with_llm_fallback(
        None, narration="some narration", vendor_name="x", ledger_name="y",
    )
    assert result.confidence == "unmapped"


def test_fallback_returns_unmapped_when_llm_returns_none(monkeypatch):
    """LLM says it can't classify → row stays unmapped, not crash."""
    from app.tally import llm_classifier as llm_mod

    null_backend = MagicMock()
    null_backend.classify.return_value = None
    null_backend.name = "null"
    monkeypatch.setattr(llm_mod, "get_llm_classifier", lambda: null_backend)

    result = classify_with_llm_fallback(
        "99999999", narration="test", vendor_name=None, ledger_name=None,
    )
    assert result.confidence == "unmapped"
    null_backend.classify.assert_called_once()
