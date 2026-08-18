# ============================================================
# schemas.py — Data Contracts & Runtime Validation
# Investment Risk BI Platform
# ============================================================

from datetime import date
from typing import Optional, List
from dataclasses import dataclass, field

try:
    from pydantic import BaseModel, Field, field_validator, ConfigDict

    class TransactionContract(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)

        tx_date: date
        ticker: str = Field(..., min_length=1, max_length=20)
        tx_type: str = Field(..., description="buy, sell, or dividend")
        quantity: float = Field(..., gt=0)
        price: float = Field(..., ge=0)
        currency: str = Field(default="EUR", min_length=3, max_length=3)
        fees: float = Field(default=0.0, ge=0)
        notes: Optional[str] = None

        @field_validator("tx_type")
        @classmethod
        def validate_tx_type(cls, v: str) -> str:
            v_clean = str(v).lower().strip()
            if v_clean not in ["buy", "sell", "dividend"]:
                raise ValueError(f"tx_type non valido: {v}. Deve essere buy, sell o dividend.")
            return v_clean

        @field_validator("currency")
        @classmethod
        def validate_currency(cls, v: str) -> str:
            return str(v).upper().strip()

    class PortfolioInputContract(BaseModel):
        portfolio_name: str = Field(default="Main Portfolio", min_length=1)
        base_currency: str = Field(default="EUR", min_length=3, max_length=3)
        transactions: List[TransactionContract] = Field(default_factory=list)

    PYDANTIC_AVAILABLE = True

except ImportError:
    PYDANTIC_AVAILABLE = False

    @dataclass
    class TransactionContract:
        tx_date: date
        ticker: str
        tx_type: str
        quantity: float
        price: float
        currency: str = "EUR"
        fees: float = 0.0
        notes: Optional[str] = None

        def __post_init__(self):
            self.tx_type = str(self.tx_type).lower().strip()
            if self.tx_type not in ["buy", "sell", "dividend"]:
                raise ValueError(f"tx_type non valido: {self.tx_type}")
            if self.quantity <= 0:
                raise ValueError("quantity deve essere maggiore di 0")
            if self.price < 0:
                raise ValueError("price non può essere negativo")
            self.currency = str(self.currency).upper().strip()

    @dataclass
    class PortfolioInputContract:
        portfolio_name: str = "Main Portfolio"
        base_currency: str = "EUR"
        transactions: List[TransactionContract] = field(default_factory=list)


def validate_transaction_records(records: list) -> tuple[list, list]:
    """
    Valida una lista di dizionari transazione secondo il contratto dati.
    Ritorna una tupla: (valid_contracts, errors)
    """
    valid_contracts = []
    errors = []

    for idx, rec in enumerate(records):
        try:
            contract = TransactionContract(
                tx_date=rec.get("tx_date"),
                ticker=str(rec.get("ticker", "")),
                tx_type=str(rec.get("tx_type", "")),
                quantity=float(rec.get("quantity", 0)),
                price=float(rec.get("price", 0)),
                currency=str(rec.get("currency", "EUR")),
                fees=float(rec.get("fees", 0.0)),
                notes=rec.get("notes")
            )
            valid_contracts.append(contract)
        except Exception as e:
            errors.append(f"Riga {idx + 1} ({rec.get('ticker', 'N/A')}): {str(e)}")

    return valid_contracts, errors
