# ============================================================
# core/wealth/wealth_models.py
# ARGUS — Wealth Management & Personal Finance Models
# Data structures, enums, and validation schemas
# ============================================================

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class AccountType(str, Enum):
    CHECKING = "checking"              # Conto corrente
    SAVINGS = "savings"                # Conto deposito / risparmio
    EMERGENCY_FUND = "emergency_fund"  # Fondo emergenza
    BROKERAGE_CASH = "brokerage_cash"  # Liquidità su broker / exchange
    CREDIT_CARD = "credit_card"        # Carta di credito (passività a breve)
    LOAN = "loan"                      # Prestito / finanziamento
    MORTGAGE = "mortgage"              # Mutuo


class CategoryNature(str, Enum):
    ESSENTIAL_NEED = "essential_need"      # 50% Needs (Casa, bollette, spesa)
    DISCRETIONARY_WANT = "discretionary_want" # 30% Wants (Ristoranti, viaggi, shopping)
    SAVING_INVESTMENT = "saving_investment"   # 20% Savings (PAC, pensione, risparmio)
    DEBT_SERVICE = "debt_service"          # Rata mutuo/prestito
    TAX = "tax"                            # Tasse e imposte
    INFLOW_ACTIVE = "inflow_active"        # Stipendio, fatturato, bonus
    INFLOW_PASSIVE = "inflow_passive"      # Dividendi, affitti, cedole


class PhysicalAssetCategory(str, Enum):
    LUXURY_WATCHES = "luxury_watches"      # Orologi di lusso (Rolex, Patek, Omega...)
    REAL_ESTATE = "real_estate"            # Immobili, terreni
    PRECIOUS_METALS = "precious_metals"    # Oro, argento, lingotti
    COLLECTIBLES = "collectibles_art"      # Arte, auto d'epoca, collezioni
    VEHICLES = "vehicles"                  # Auto, moto
    OTHER = "other"


@dataclass
class WealthAccount:
    account_id: Optional[int]
    name: str
    account_type: str = AccountType.CHECKING.value
    institution: str = "Banca"
    currency: str = "EUR"
    balance: float = 0.0
    is_active: bool = True
    iban: Optional[str] = None
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None


@dataclass
class WealthCategory:
    category_id: Optional[int]
    name: str
    flow_type: str  # 'income', 'expense', 'transfer'
    nature: str = CategoryNature.ESSENTIAL_NEED.value
    parent_id: Optional[int] = None
    icon: str = "🏷️"
    color: str = "#6366f1"
    is_system: bool = False


@dataclass
class WealthCashflowItem:
    tx_id: Optional[int]
    account_id: int
    category_id: int
    tx_date: date
    amount: float
    currency: str = "EUR"
    direction: str = "outflow"  # 'inflow', 'outflow', 'transfer'
    merchant: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: bool = False
    payment_method: str = "Carta / Bonifico"
    tags: Optional[str] = None


@dataclass
class PhysicalAssetItem:
    asset_id: Optional[int]
    name: str
    asset_category: str = PhysicalAssetCategory.LUXURY_WATCHES.value
    brand_or_location: Optional[str] = None
    model_or_specs: Optional[str] = None
    reference_number: Optional[str] = None
    acquisition_date: Optional[date] = None
    purchase_price: float = 0.0
    current_market_value: float = 0.0
    valuation_date: Optional[date] = None
    valuation_source: str = "Stima di Mercato"
    condition_grade: str = "Eccellente / Full Set"
    currency: str = "EUR"
    notes: Optional[str] = None


@dataclass
class PensionPlanItem:
    plan_id: Optional[int]
    plan_name: str
    provider: str
    plan_type: str = "fondo_pensione_aperto"
    accumulated_value: float = 0.0
    monthly_employee_contrib: float = 0.0
    monthly_employer_contrib: float = 0.0
    tax_deductible_annual: float = 0.0
    expected_retirement_age: int = 67
    currency: str = "EUR"
    investment_line: str = "Azionario / Crescita"
    notes: Optional[str] = None


@dataclass
class NetWorthSummary:
    total_net_worth: float = 0.0
    liquid_cash: float = 0.0
    financial_investments: float = 0.0  # Da portafogli titoli / crypto
    physical_assets: float = 0.0
    luxury_watches_total: float = 0.0
    real_estate_total: float = 0.0
    precious_metals_total: float = 0.0
    pension_total: float = 0.0
    total_liabilities: float = 0.0
    emergency_fund_amount: float = 0.0
    monthly_burn_rate: float = 0.0
    runway_months: float = 0.0
    savings_rate_pct: float = 0.0
    wealth_health_score: float = 0.0
    as_of_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    @property
    def real_estate_equity(self) -> float:
        return max(0.0, self.real_estate_total - self.total_liabilities)



class GoalCategory(str, Enum):
    FIRE = "fire"
    REAL_ESTATE = "real_estate"
    EDUCATION = "education"
    RETIREMENT = "retirement"
    LUXURY = "luxury"
    EMERGENCY_BUFFER = "emergency_buffer"
    CUSTOM = "custom"


@dataclass
class WealthGoalItem:
    goal_id: Optional[int]
    name: str
    target_amount: float
    target_date: date
    portfolio_id: int = 1
    current_amount: float = 0.0
    monthly_contribution: float = 0.0
    category: str = GoalCategory.CUSTOM.value
    priority: str = "medium"  # high, medium, low
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive
    inflation_rate: float = 0.02
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class HeirRelationship(str, Enum):
    SPOUSE = "spouse"                    # Coniuge (Franchigia 1.000.000€, aliquota 4%)
    CHILD = "child"                      # Figlio / Discendente in linea retta (Franchigia 1.000.000€, aliquota 4%)
    PARENT = "parent"                    # Genitore / Ascendente in linea retta (Franchigia 1.000.000€, aliquota 4%)
    SIBLING = "sibling"                  # Fratello / Sorella (Franchigia 100.000€, aliquota 6%)
    RELATIVE_4TH = "relative_4th"        # Altri parenti fino al 4° grado / affini (Nessuna franchigia, aliquota 6%)
    OTHER = "other"                      # Altri soggetti / estranei (Nessuna franchigia, aliquota 8%)
    DISABLED = "disabled"                # Portatore di handicap grave L. 104 (Franchigia 1.500.000€)


@dataclass
class EstateHeirItem:
    heir_id: Optional[int]
    name: str
    relationship: str = HeirRelationship.CHILD.value
    is_disabled: bool = False
    assigned_share_pct: float = 0.0  # Quota testamentaria assegnata (%)
    notes: Optional[str] = None


@dataclass
class EstatePlanResult:
    gross_estate: float = 0.0
    exempt_assets: float = 0.0  # BTP, Titoli di Stato, Polizze Vita, Fondi Pensione
    taxable_estate: float = 0.0
    total_liabilities: float = 0.0
    net_taxable_estate: float = 0.0
    heir_breakdowns: List[Dict[str, Any]] = field(default_factory=list)
    total_inheritance_tax: float = 0.0
    total_mortgage_cadastral_tax: float = 0.0
    total_tax_burden: float = 0.0
    effective_tax_rate_pct: float = 0.0
    disposable_quota_pct: float = 0.0
    legitimate_quota_pct: float = 0.0


# Alias per compatibilità
WealthConsolidatedSummary = NetWorthSummary


@dataclass
class RebalanceDriftItem:
    asset_name: str
    asset_class: str
    current_value_eur: float
    current_weight_pct: float
    target_weight_pct: float
    drift_pct: float
    drift_status: str  # "CRITICAL", "MODERATE", "IN_LINE"
    action_type: str   # "BUY", "SELL", "HOLD"
    target_delta_eur: float
    is_tax_advantaged: bool = False
    notes: Optional[str] = None


@dataclass
class RealEstateEquitySummary:
    total_property_market_value: float = 0.0
    total_mortgage_debt_remaining: float = 0.0
    net_home_equity_eur: float = 0.0
    weighted_ltv_pct: float = 0.0
    total_monthly_mortgage_cost: float = 0.0
    property_count: int = 0
    mortgage_count: int = 0
    properties_detail: List[Dict[str, Any]] = field(default_factory=list)


class LegalEntityType(str, Enum):
    PERSONA_FISICA = "persona_fisica"             # Persona fisica residente (IRPEF / 26%)
    HOLDING_SRL = "holding_srl"                   # Holding di partecipazioni SRL / SpA (IRES 24%, PEX 1.2%)
    SOCIETA_SEMPLICE = "societa_semplice"         # Società Semplice / Cassaforte Familiare (trasparenza)
    TRUST_FAMILIARE = "trust_familiare"           # Trust di protezione patrimoniale e successoria
    POLIZZA_ISTITUZIONALE = "polizza_dedicata"     # Polizza vita Ramo I/III Private Insurance


@dataclass
class FamilyOfficeEntityItem:
    entity_id: str
    name: str
    entity_type: str = LegalEntityType.PERSONA_FISICA.value
    gross_assets_eur: float = 0.0
    third_party_liabilities_eur: float = 0.0
    intercompany_receivables_eur: float = 0.0  # Crediti verso altre entità del gruppo
    intercompany_liabilities_eur: float = 0.0  # Debiti verso soci / altre entità del gruppo
    ownership_share_pct: float = 100.0         # Quota di possesso del nucleo familiare
    effective_tax_rate_est: float = 26.0       # Aliquota media stimata su redditi di capitale
    jurisdiction: str = "Italia"
    notes: Optional[str] = None


@dataclass
class SRRScenarioResult:
    scenario_name: str
    final_wealth_eur: float
    ruin_year: Optional[int]
    is_ruined: bool
    wealth_trajectory: List[float]
    cumulative_withdrawals_eur: float
    glide_buffer_recommended_eur: float


@dataclass
class QuarterlyReviewResult:
    quarter: str
    generated_at: str
    executive_summary_text: str
    macro_outlook_text: str
    performance_attribution_text: str
    goals_progress_text: str
    tactical_recommendations: List[str]
    consolidated_kpis: Dict[str, Any]


# ── PRIVATE EQUITY & REAL ASSETS MODELS ──────────────────────

@dataclass
class PECashflowItem:
    date: str
    amount_eur: float  # Negativo per investimenti/capital call, positivo per distribuzioni
    cashflow_type: str  # "CAPITAL_CALL", "DISTRIBUTION", "DIVIDEND", "EXIT"
    note: Optional[str] = None


@dataclass
class PrivateEquityDealItem:
    deal_id: str
    name: str
    asset_class: str = "Venture Capital"  # "Private Equity", "Venture Capital", "Real Estate Deal", "Club Deal"
    committed_capital_eur: float = 100000.0
    called_capital_eur: float = 80000.0
    distributions_received_eur: float = 30000.0
    current_nav_estimated_eur: float = 95000.0
    vintage_year: int = 2021
    status: str = "ACTIVE"  # "ACTIVE", "EXITED", "WRITTEN_OFF"
    irr_net_pct: Optional[float] = None
    moic_multiple: Optional[float] = None
    cashflows: List[PECashflowItem] = field(default_factory=list)


@dataclass
class PEDealMetrics:
    total_committed_eur: float
    total_called_eur: float
    total_distributed_eur: float
    total_current_nav_eur: float
    unfunded_commitment_eur: float
    portfolio_xirr_pct: float
    portfolio_moic_tvpi: float
    dpi_multiple: float
    rvpi_multiple: float
    deals_count: int
    j_curve_df: Any = None


# ── MULTI-CURRENCY FX HEDGING MODELS ─────────────────────────

@dataclass
class FXExposureItem:
    currency: str
    nominal_amount_eur: float
    weight_pct: float
    local_interest_rate_pct: float
    annual_forward_points_cost_pct: float
    hedged_ratio_pct: float = 0.0


@dataclass
class FXHedgingResult:
    total_wealth_eur: float
    base_currency: str
    foreign_exposure_eur: float
    foreign_exposure_pct: float
    exposures: List[FXExposureItem]
    annual_hedging_cost_eur: float
    unhedged_drawdown_risk_eur: float  # Shock -15% FX
    hedged_scenario_comparison: Dict[str, Any]


# ── FAMILY GOVERNANCE & PATTO DI FAMIGLIA MODELS ─────────────

@dataclass
class PattoFamigliaResult:
    business_value_eur: float
    assigned_heir_name: str
    assigned_quota_pct: float
    non_assigned_heirs: List[Dict[str, Any]]
    total_compensation_due_eur: float
    tax_exempt_under_art_768_bis: bool
    is_legitimate_shielded: bool
    governance_checklist: List[str]


@dataclass
class FamilyGovernancePlan:
    total_family_wealth_eur: float
    staggered_donations_schedule: List[Dict[str, Any]]
    total_tax_savings_vs_direct_inheritance_eur: float
    patto_di_famiglia: Optional[PattoFamigliaResult]


# ── MULTI-ASSET TOTAL WEALTH BRINSON ATTRIBUTION ─────────────

@dataclass
class BrinsonWealthBucketItem:
    asset_class: str
    portfolio_weight_pct: float
    benchmark_weight_pct: float
    portfolio_return_pct: float
    benchmark_return_pct: float
    allocation_effect_pct: float
    selection_effect_pct: float
    interaction_effect_pct: float
    total_contribution_pct: float


@dataclass
class BrinsonWealthResult:
    portfolio_total_return_pct: float
    benchmark_total_return_pct: float
    excess_return_pct: float
    allocation_effect_total_pct: float
    selection_effect_total_pct: float
    interaction_effect_total_pct: float
    breakdown_table: List[BrinsonWealthBucketItem]


# ── SMART CASHFLOW RECONCILIATION MODELS ─────────────────────

@dataclass
class ReconciliationMatchItem:
    tx_date: str
    description: str
    amount_eur: float
    matched_category: str
    match_confidence_pct: float
    match_source: str  # "RECURRING_EXPENSE", "MORTGAGE", "SALARY", "MANUAL"
    is_duplicate: bool = False


@dataclass
class ReconciliationResult:
    total_transactions_processed: int
    matched_transactions_count: int
    unmatched_transactions_count: int
    duplicates_flagged_count: int
    reconciliation_rate_pct: float
    matches: List[ReconciliationMatchItem]

