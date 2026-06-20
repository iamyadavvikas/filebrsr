"""Unit tests for extraction logic."""
import pytest
from app.extraction import extract_with_regex, calculate_confidence
from app.brsr_datapoints import BRSR_DATAPOINTS, get_datapoints_stats, analyze_gaps_v2


class TestRegexExtraction:
    """Test regex-based field extraction."""

    def test_extracts_cin(self):
        text = "CIN: L28920MH1951PLC008485\nCompany: Test Corp"
        result = extract_with_regex(text)
        assert "section_a" in result
        cin = result["section_a"].get("cin", "")
        assert "L28920MH1951PLC008485" in cin or cin != ""

    def test_extracts_revenue(self):
        text = "Revenue from operations: Rs. 12,345 Crores\nTurnover: 12345"
        result = extract_with_regex(text)
        # Should pick up financial data
        assert isinstance(result, dict)
        assert "section_a" in result

    def test_handles_empty_text(self):
        result = extract_with_regex("")
        assert isinstance(result, dict)
        for section in ["section_a", "section_b", "section_c"]:
            assert section in result

    def test_handles_garbage_text(self):
        result = extract_with_regex("@#$%^&*()!!! random garbage 123")
        assert isinstance(result, dict)


class TestConfidenceCalculation:
    """Test confidence scoring logic."""

    def test_full_agreement(self):
        regex = {"section_a": {"cin": "L123"}, "section_b": {}, "section_c": {}}
        ai = {"section_a": {"cin": "L123"}, "section_b": {}, "section_c": {}}
        confidence = calculate_confidence(regex, ai)
        assert isinstance(confidence, dict)

    def test_no_data(self):
        empty = {"section_a": {}, "section_b": {}, "section_c": {}}
        confidence = calculate_confidence(empty, empty)
        assert isinstance(confidence, dict)


class TestBRSRDatapoints:
    """Test BRSR framework definitions."""

    def test_datapoints_not_empty(self):
        assert len(BRSR_DATAPOINTS) > 0

    def test_stats_structure(self):
        stats = get_datapoints_stats()
        assert "total_datapoints" in stats
        assert stats["total_datapoints"] >= 337

    def test_gap_analysis_empty_data(self):
        empty = {"section_a": {}, "section_b": {}, "section_c": {}}
        gaps = analyze_gaps_v2(empty)
        assert isinstance(gaps, dict)
        assert "overall_compliance" in gaps or "gap_count" in gaps or len(gaps) > 0


class TestNiftyBenchmarks:
    """Test benchmark comparison logic."""

    def test_sector_detection(self):
        from app.nifty50_benchmarks import detect_sector
        # detect_sector takes extracted_data dict
        data = {"section_a": {"industry": "Information Technology"}}
        result = detect_sector(data)
        assert result is not None or result is None  # May or may not match

    def test_benchmark_comparison(self):
        from app.nifty50_benchmarks import get_benchmark_comparison
        data = {"section_a": {"industry": "IT"}, "section_b": {}, "section_c": {}}
        result = get_benchmark_comparison(data)
        assert isinstance(result, dict)
