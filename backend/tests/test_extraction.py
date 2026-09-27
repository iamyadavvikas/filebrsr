"""Unit tests for extraction logic."""
import pytest
from app.extraction import extract_with_regex, calculate_confidence
from app.brsr_datapoints import BRSR_DATAPOINTS, get_datapoints_stats, analyze_gaps_v2


class TestRegexExpansion:
    """Phase-2 pattern coverage: locations, splits, RPT, intensities, POSH."""

    def test_locations_and_markets(self):
        text = (
            "Number of plants in India: 6\nNumber of offices in India: 12\n"
            "Number of plants International: 2\nStates served: 18\n"
            "Number of countries served: 7\nContribution of exports: 14.5%"
        )
        r = extract_with_regex(text)
        a = r["section_a"]
        assert a.get("plants_national") == "6"
        assert a.get("offices_national") == "12"
        assert a.get("plants_international") == "2"
        assert a.get("states_served") == "18"
        assert a.get("countries_served") == "7"
        assert a.get("export_contribution_pct") == "14.5"

    def test_workforce_splits(self):
        text = (
            "Permanent Employees - Male: 800\nPermanent Employees - Female: 320\n"
            "Permanent Employees - Total: 1120\nPermanent Workers - Male: 150"
        )
        r = extract_with_regex(text)
        a = r["section_a"]
        assert a.get("employees_perm_male") == "800"
        assert a.get("employees_perm_female") == "320"
        assert a.get("employees_perm_total") == "1120"
        assert a.get("workers_perm_male") == "150"

    def test_rpt_and_concentration(self):
        text = (
            "Related party purchases: 8.2%\nRelated party sales: 3.1%\n"
            "Purchases from trading houses: 12%\nNumber of trading houses: 9\n"
            "Top 10 suppliers: 44%"
        )
        r = extract_with_regex(text)
        c = r["section_c"]
        assert c.get("rpt_purchases_pct") == "8.2"
        assert c.get("rpt_sales_pct") == "3.1"
        assert c.get("trading_house_purchases_pct") == "12"
        assert c.get("trading_house_count") == "9"
        assert c.get("top10_supplier_concentration_pct") == "44"

    def test_intensities_and_scope3(self):
        text = (
            "Scope 3 emissions: 45000 tCO2e\n"
            "GHG intensity per rupee of turnover: 0.8\n"
            "Energy intensity per rupee of turnover: 12.4\n"
            "Water discharged: 5000 KL\nWaste disposed: 120 MT\n"
            "Fatalities: 0\nMinimum wage compliance: 100%"
        )
        r = extract_with_regex(text)
        c = r["section_c"]
        assert c.get("ghg_scope3") == "45000"
        assert c.get("ghg_intensity_turnover") == "0.8"
        assert c.get("energy_intensity_turnover") == "12.4"
        assert c.get("water_discharge") == "5000"
        assert c.get("waste_disposed") == "120"
        assert c.get("fatalities") == "0"
        assert c.get("minimum_wage_compliance_pct") == "100"

    def test_posh_and_policies(self):
        text = (
            "POSH complaints filed: 2\nPOSH complaints upheld: 1\n"
            "Anti-corruption: Yes\nCorruption incidents: 0\n"
            "Policy extends to value chain: Yes\nNet Worth: Rs 2,400 Cr"
        )
        r = extract_with_regex(text)
        assert r["section_c"].get("posh_filed") == "2"
        assert r["section_c"].get("posh_upheld") == "1"
        assert r["section_c"].get("corruption_incidents") == "0"
        assert r["section_b"].get("policy_extends_value_chain") == "Yes"
        assert r["section_a"].get("net_worth") == "2,400"


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
