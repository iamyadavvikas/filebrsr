"""
Indian Carbon Emission Factors for GHG Protocol-aligned calculations.

Sources:
- Central Electricity Authority (CEA) CO2 Baseline Database (versioned JSON
  under ``factors/cea/`` — loaded via :mod:`app.factors_india`)
- IPCC AR6 emission factors
- India GHG Program (WRI India + CII)
- Bureau of Energy Efficiency (BEE) PAT Scheme

Note: ``CEA_GRID_EMISSION_FACTORS`` and ``STATE_GRID_FACTORS`` are now built
from the versioned ``factors/`` registry rather than declared inline. Other
factor tables (Scope 1 fuels, Scope 3 categories, refrigerants, steam, PAT
benchmarks) remain literal here pending future factors-india slices.
"""

# Re-exported from the JSON-backed registry. Same dict shape as the
# previous inline literal so router_platform.py and other callers are
# unchanged.
from app.factors_india._legacy import (  # noqa: E402  (kept near related imports below)
    CEA_GRID_EMISSION_FACTORS,
    STATE_GRID_FACTORS,
)

# Scope 1: Stationary Combustion (tCO2e per unit)
STATIONARY_COMBUSTION_FACTORS = {
    "coal": {"unit": "MT", "co2": 2.4569, "ch4": 0.0001, "n2o": 0.00004, "source": "IPCC 2006"},
    "lignite": {"unit": "MT", "co2": 1.1010, "ch4": 0.0001, "n2o": 0.00002, "source": "IPCC 2006"},
    "natural_gas": {"unit": "SCM", "co2": 0.00202, "ch4": 0.0000001, "n2o": 0.000000002, "source": "IPCC 2006"},
    "lng": {"unit": "MT", "co2": 2.7500, "ch4": 0.0001, "n2o": 0.00003, "source": "IPCC 2006"},
    "diesel_dg_set": {"unit": "KL", "co2": 2.6413, "ch4": 0.0001, "n2o": 0.00004, "source": "IPCC 2006"},
    "furnace_oil": {"unit": "KL", "co2": 3.0759, "ch4": 0.0001, "n2o": 0.00004, "source": "IPCC 2006"},
    "lpg": {"unit": "MT", "co2": 2.9498, "ch4": 0.0001, "n2o": 0.00006, "source": "IPCC 2006"},
    "pet_coke": {"unit": "MT", "co2": 3.1905, "ch4": 0.0001, "n2o": 0.00004, "source": "IPCC 2006"},
    "biomass_briquettes": {"unit": "MT", "co2": 0.0, "ch4": 0.0003, "n2o": 0.00004, "source": "IPCC 2006"},  # CO2 neutral
    "rice_husk": {"unit": "MT", "co2": 0.0, "ch4": 0.0003, "n2o": 0.00004, "source": "IPCC 2006"},
}

# Scope 1: Mobile Combustion (tCO2e per KL)
MOBILE_COMBUSTION_FACTORS = {
    "petrol": {"unit": "KL", "co2": 2.2460, "ch4": 0.0001, "n2o": 0.00005, "source": "IPCC 2006"},
    "diesel": {"unit": "KL", "co2": 2.6413, "ch4": 0.00004, "n2o": 0.00004, "source": "IPCC 2006"},
    "cng": {"unit": "kg", "co2": 0.00275, "ch4": 0.000005, "n2o": 0.0000001, "source": "IPCC 2006"},
}

# Scope 1: Fugitive Emissions
REFRIGERANT_GWP = {
    "R-22": 1810,
    "R-134a": 1430,
    "R-410A": 2088,
    "R-407C": 1774,
    "R-32": 675,
    "CO2_refrigerant": 1,
    "SF6": 22800,
}

# Scope 2: Purchased Electricity (location-based)
# STATE_GRID_FACTORS is now imported from app.factors_india._legacy at the top
# of this module. Slice 1 only exposes the "national" key; SLDC state-level
# overrides will repopulate this dict in factors-india slice 2.

# Scope 2: Purchased Steam/Heating (tCO2e per GJ)
STEAM_EMISSION_FACTORS = {
    "natural_gas_boiler": 0.0679,
    "coal_boiler": 0.1300,
    "oil_boiler": 0.0940,
}

# Scope 3: Category-wise default factors
SCOPE_3_FACTORS = {
    "business_travel_air_domestic": {"unit": "passenger_km", "factor": 0.000158, "source": "DEFRA 2024"},
    "business_travel_air_short_haul": {"unit": "passenger_km", "factor": 0.000158, "source": "DEFRA 2024"},
    "business_travel_air_long_haul": {"unit": "passenger_km", "factor": 0.000110, "source": "DEFRA 2024"},
    "business_travel_rail": {"unit": "passenger_km", "factor": 0.000041, "source": "India Railways"},
    "business_travel_road_car": {"unit": "km", "factor": 0.000171, "source": "DEFRA 2024"},
    "employee_commute_car": {"unit": "km", "factor": 0.000171, "source": "DEFRA 2024"},
    "employee_commute_two_wheeler": {"unit": "km", "factor": 0.000073, "source": "DEFRA 2024"},
    "employee_commute_bus": {"unit": "passenger_km", "factor": 0.000089, "source": "DEFRA 2024"},
    "employee_commute_metro": {"unit": "passenger_km", "factor": 0.000033, "source": "DEFRA 2024"},
    "waste_landfill": {"unit": "MT", "factor": 0.580, "source": "IPCC 2006"},
    "waste_incineration": {"unit": "MT", "factor": 0.986, "source": "IPCC 2006"},
    "waste_composting": {"unit": "MT", "factor": 0.010, "source": "IPCC 2006"},
    "waste_recycling": {"unit": "MT", "factor": 0.021, "source": "IPCC 2006"},
    "water_supply": {"unit": "KL", "factor": 0.000344, "source": "India WRI"},
    "water_treatment": {"unit": "KL", "factor": 0.000708, "source": "India WRI"},
    "paper_procurement": {"unit": "MT", "factor": 0.919, "source": "DEFRA 2024"},
    "freight_road": {"unit": "tonne_km", "factor": 0.000108, "source": "DEFRA 2024"},
    "freight_rail": {"unit": "tonne_km", "factor": 0.000028, "source": "India Railways"},
    "freight_sea": {"unit": "tonne_km", "factor": 0.000016, "source": "DEFRA 2024"},
}

# PAT Scheme - Sector-specific energy benchmarks (TOE per unit production)
# Source: Bureau of Energy Efficiency (BEE)
PAT_SECTOR_BENCHMARKS = {
    "aluminium": {"unit": "TOE/MT", "target_sec": 7.5, "gate_sec": 8.0},
    "cement": {"unit": "TOE/MT_clinker", "target_sec": 0.068, "gate_sec": 0.074},
    "chlor_alkali": {"unit": "TOE/MT_caustic", "target_sec": 0.84, "gate_sec": 0.90},
    "fertilizer": {"unit": "TOE/MT_urea", "target_sec": 0.55, "gate_sec": 0.60},
    "iron_steel": {"unit": "TOE/MT_crude_steel", "target_sec": 0.55, "gate_sec": 0.62},
    "paper_pulp": {"unit": "TOE/MT_paper", "target_sec": 0.75, "gate_sec": 0.85},
    "textile": {"unit": "TOE/MT", "target_sec": 0.35, "gate_sec": 0.40},
    "thermal_power": {"unit": "kcal/kWh", "target_sec": 2400, "gate_sec": 2500},
    "refinery": {"unit": "MBN", "target_sec": 58, "gate_sec": 65},
    "railways": {"unit": "TOE/BTKM", "target_sec": 3.5, "gate_sec": 4.0},
}

# BRSR-specific disclosure fields for energy/emissions
BRSR_ENERGY_FIELDS = {
    "total_electricity_consumed_gj": "C.P6.E.1",
    "total_fuel_consumed_gj": "C.P6.E.2",
    "energy_from_renewable_gj": "C.P6.E.3",
    "energy_from_non_renewable_gj": "C.P6.E.4",
    "energy_intensity_per_revenue": "C.P6.E.5",
    "scope_1_emissions_tco2e": "C.P6.GHG.1",
    "scope_2_emissions_tco2e": "C.P6.GHG.2",
    "scope_3_emissions_tco2e": "C.P6.GHG.3",
    "ghg_intensity_per_revenue": "C.P6.GHG.4",
}


def calculate_scope1_emissions(fuel_type: str, quantity: float) -> dict:
    """Calculate Scope 1 emissions from fuel consumption."""
    factors = STATIONARY_COMBUSTION_FACTORS.get(fuel_type) or MOBILE_COMBUSTION_FACTORS.get(fuel_type)
    if not factors:
        return {"error": f"Unknown fuel type: {fuel_type}"}
    
    co2 = quantity * factors["co2"]
    ch4 = quantity * factors["ch4"] * 28  # GWP of CH4
    n2o = quantity * factors["n2o"] * 265  # GWP of N2O
    total = co2 + ch4 + n2o
    
    return {
        "fuel_type": fuel_type,
        "quantity": quantity,
        "unit": factors["unit"],
        "co2_tonnes": round(co2, 4),
        "ch4_co2e_tonnes": round(ch4, 4),
        "n2o_co2e_tonnes": round(n2o, 4),
        "total_tco2e": round(total, 4),
        "source": factors["source"],
    }


def calculate_scope2_emissions(electricity_mwh: float, fy: str = "FY2023-24", state: str = "national") -> dict:
    """Calculate Scope 2 emissions from purchased electricity."""
    grid_factor = STATE_GRID_FACTORS.get(state, STATE_GRID_FACTORS["national"])
    cea_factor = CEA_GRID_EMISSION_FACTORS.get(fy, CEA_GRID_EMISSION_FACTORS["default"])
    
    # Use CEA national factor for reporting (BRSR standard)
    emissions = electricity_mwh * cea_factor
    
    return {
        "electricity_mwh": electricity_mwh,
        "grid_emission_factor": cea_factor,
        "state_factor": grid_factor,
        "total_tco2e": round(emissions, 4),
        "source": f"CEA CO2 Database {fy}",
        "method": "location_based",
    }


def calculate_scope3_emissions(category: str, quantity: float) -> dict:
    """Calculate Scope 3 emissions by category."""
    factors = SCOPE_3_FACTORS.get(category)
    if not factors:
        return {"error": f"Unknown category: {category}"}
    
    emissions = quantity * factors["factor"]
    
    return {
        "category": category,
        "quantity": quantity,
        "unit": factors["unit"],
        "emission_factor": factors["factor"],
        "total_tco2e": round(emissions, 4),
        "source": factors["source"],
    }


def calculate_energy_intensity(total_energy_gj: float, revenue_crores: float, turnover_based: bool = True) -> dict:
    """Calculate energy intensity ratio as per BRSR format."""
    if revenue_crores <= 0:
        return {"error": "Revenue must be positive"}
    
    intensity = total_energy_gj / revenue_crores
    
    return {
        "total_energy_gj": total_energy_gj,
        "denominator": "revenue_crores" if turnover_based else "production_units",
        "denominator_value": revenue_crores,
        "intensity": round(intensity, 4),
        "unit": "GJ/Cr" if turnover_based else "GJ/unit",
    }


def calculate_ghg_intensity(total_emissions_tco2e: float, revenue_crores: float) -> dict:
    """Calculate GHG intensity ratio as per BRSR format."""
    if revenue_crores <= 0:
        return {"error": "Revenue must be positive"}
    
    intensity = total_emissions_tco2e / revenue_crores
    
    return {
        "total_emissions_tco2e": total_emissions_tco2e,
        "revenue_crores": revenue_crores,
        "intensity": round(intensity, 4),
        "unit": "tCO2e/Cr",
    }


def get_pat_compliance(sector: str, actual_sec: float) -> dict:
    """Check PAT scheme compliance for a designated consumer."""
    benchmark = PAT_SECTOR_BENCHMARKS.get(sector)
    if not benchmark:
        return {"error": f"Sector '{sector}' not in PAT scheme"}
    
    target = benchmark["target_sec"]
    gate = benchmark["gate_sec"]
    
    status = "compliant" if actual_sec <= target else "non_compliant"
    excess = max(0, actual_sec - target)
    escerts_potential = round(excess * -1 if actual_sec < target else 0, 2)  # Negative = savings
    
    return {
        "sector": sector,
        "actual_sec": actual_sec,
        "target_sec": target,
        "gate_sec": gate,
        "unit": benchmark["unit"],
        "status": status,
        "deviation_percent": round(((actual_sec - target) / target) * 100, 2),
        "escerts_potential": escerts_potential,
    }


# SEBI BRSR Compliance Calendar for Indian listed companies
SEBI_COMPLIANCE_CALENDAR = [
    {
        "title": "BRSR Filing Deadline (Top 1000)",
        "description": "Annual BRSR report submission to stock exchanges along with Annual Report",
        "regulatory_body": "SEBI",
        "month": 9,  # September (within 60 days of AGM, which is before Sept 30)
        "day": 30,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "top_1000",
    },
    {
        "title": "BRSR Core Assurance Report (Top 250)",
        "description": "Third-party reasonable assurance on BRSR Core indicators",
        "regulatory_body": "SEBI",
        "month": 9,
        "day": 30,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "top_250",
    },
    {
        "title": "ESG Disclosure to BSE",
        "description": "Submit Business Responsibility and Sustainability Report to BSE Listing Centre",
        "regulatory_body": "BSE",
        "month": 10,
        "day": 15,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "all_listed",
    },
    {
        "title": "ESG Disclosure to NSE",
        "description": "Submit BRSR to NSE NEAPS portal",
        "regulatory_body": "NSE",
        "month": 10,
        "day": 15,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "all_listed",
    },
    {
        "title": "CDP Disclosure Deadline",
        "description": "Carbon Disclosure Project questionnaire response deadline (voluntary but recommended)",
        "regulatory_body": "CDP",
        "month": 7,
        "day": 31,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "voluntary",
    },
    {
        "title": "Board CSR Committee Meeting",
        "description": "Quarterly review of CSR activities and BRSR data collection progress",
        "regulatory_body": "Internal",
        "month": None,
        "day": None,
        "recurring": True,
        "pattern": "quarterly",
        "applies_to": "all",
    },
    {
        "title": "GRI Report Publication",
        "description": "Global Reporting Initiative aligned sustainability report (if applicable)",
        "regulatory_body": "GRI",
        "month": 12,
        "day": 31,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "voluntary",
    },
    {
        "title": "DJSI Assessment Window",
        "description": "Dow Jones Sustainability Index corporate sustainability assessment",
        "regulatory_body": "S&P Global",
        "month": 4,
        "day": 30,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "nifty50",
    },
    {
        "title": "Annual Report Filing (BSE/NSE)",
        "description": "Filing of Annual Report including BRSR with stock exchanges within 21 days of AGM",
        "regulatory_body": "SEBI",
        "month": 10,
        "day": 21,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "all_listed",
    },
    {
        "title": "Secretarial Compliance Report",
        "description": "Annual secretarial compliance report to stock exchanges (SEBI LODR Reg 24A)",
        "regulatory_body": "SEBI",
        "month": 5,
        "day": 30,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "all_listed",
    },
    {
        "title": "Corporate Governance Report (Q4)",
        "description": "Quarterly compliance report on corporate governance (Reg 27)",
        "regulatory_body": "SEBI",
        "month": 4,
        "day": 15,
        "recurring": True,
        "pattern": "quarterly",
        "applies_to": "all_listed",
    },
    {
        "title": "TCFD Disclosure Alignment",
        "description": "Voluntary TCFD-aligned climate risk disclosure (recommended by SEBI for top 250)",
        "regulatory_body": "TCFD",
        "month": 12,
        "day": 31,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "top_250",
    },
    {
        "title": "MSCI ESG Rating Assessment",
        "description": "MSCI ESG Ratings annual review window — data collection and verification",
        "regulatory_body": "MSCI",
        "month": 6,
        "day": 30,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "voluntary",
    },
    {
        "title": "Sustainalytics ESG Risk Rating",
        "description": "Annual ESG Risk Rating update by Morningstar Sustainalytics",
        "regulatory_body": "Sustainalytics",
        "month": 3,
        "day": 31,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "voluntary",
    },
    {
        "title": "MCA CSR Annual Return (Form CSR-2)",
        "description": "Filing of CSR-2 annual return with Ministry of Corporate Affairs",
        "regulatory_body": "MCA",
        "month": 3,
        "day": 31,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "all",
    },
    {
        "title": "BRSR Core - Value Chain (Top 250)",
        "description": "BRSR Core reporting for top 250 companies' value chain partners (phased from FY26)",
        "regulatory_body": "SEBI",
        "month": 9,
        "day": 30,
        "recurring": True,
        "pattern": "annual",
        "applies_to": "top_250",
    },
]
