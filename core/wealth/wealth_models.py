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
