# ==============================================================================
# core/compliance_gate.py
# ARGUS — Institutional Pre-Trade Risk & Compliance Gateway (MiFID II RTS 28)
# Pre-Trade Limits • SEC Rule 15c3-5 • Fat-Finger • ADV Slicing • Price Collars
# ==============================================================================

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ComplianceStatus(str, Enum):
    APPROVED = "APPROVED"
    WARNING = "WARNING"
    REJECTED_FAT_FINGER = "REJECTED_FAT_FINGER"
    REJECTED_ADV_LIMIT = "REJECTED_ADV_LIMIT"
    REJECTED_COLLAR_BREACH = "REJECTED_COLLAR_BREACH"
    REJECTED_INSUFFICIENT_FUNDS = "REJECTED_INSUFFICIENT_FUNDS"
    REJECTED_RESTRICTED_SYMBOL = "REJECTED_RESTRICTED_SYMBOL"


@dataclass
class PreTradeComplianceConfig:
    """Configurazione soglie di conformità pre-trade conformi a MiFID II e standard istituzionali."""

    max_notional_per_order_eur: float = 500_000.0  # Fat-finger ceiling (€500k default)
    max_adv_participation_pct: float = 15.0  # Max 15% del Volume Medio Giornaliero
    max_price_collar_pct: float = 5.0  # Max +/- 5% di scostamento dal last price
    enforce_cash_coverage: bool = True  # Verifica capienza liquidità per ordini BUY
    cash_buffer_pct: float = 1.0  # 1% buffer per commissioni e slippage
    restricted_symbols: List[str] = field(default_factory=list)


@dataclass
class PreTradeOrderRequest:
    """Rappresenta la richiesta di emissione di un ordine per la verifica pre-trade."""

    order_id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    order_qty: float
    limit_price: float
    order_type: str = "LIMIT"  # "LIMIT" or "MARKET"
    reference_price: Optional[float] = None  # Ultimo prezzo noto a mercato
    adv_shares: Optional[float] = None  # Average Daily Volume a 20/30 giorni
    available_cash_eur: Optional[float] = None  # Liquidità disponibile nel conto/portafoglio
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ComplianceVerdict:
    """Verdetto formale di compliance con hash crittografico per audit trail."""

    order_id: str
    symbol: str
    status: ComplianceStatus
    passed: bool
    notional_eur: float
    rejection_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    audit_hash: str = ""
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["status"] = self.status.value
        return res


class PreTradeRiskGate:
    """
    Gateway istituzionale di validazione pre-trade conforme a MiFID II RTS 28 e SEC Rule 15c3-5.
    Blocca ordini anomali, violazioni di prezzo limite e ordini che prosciugano la liquidità.
    """

    def __init__(self, config: Optional[PreTradeComplianceConfig] = None):
        self.config = config or PreTradeComplianceConfig()
        self._audit_log: List[ComplianceVerdict] = []

    def evaluate_order(
        self,
        order: PreTradeOrderRequest,
        portfolio_cash: Optional[float] = None,
    ) -> ComplianceVerdict:
        """
        Esegue la catena di verifiche pre-trade deterministiche su un singolo ordine.
        """
        rejection_reasons = []
        warnings = []
        status = ComplianceStatus.APPROVED

        # Calcolo del prezzo effettivo per la valorizzazione del nozionale
        ref_px = order.reference_price if (order.reference_price and order.reference_price > 0) else order.limit_price
        exec_px = order.limit_price if (order.limit_price and order.limit_price > 0) else ref_px
        notional_eur = abs(float(order.order_qty) * float(exec_px))

        # 1. Verifica Simboli Soggetti a Restrizione o Sanzioni
        if order.symbol.upper() in [s.upper() for s in self.config.restricted_symbols]:
            rejection_reasons.append(f"Strumento {order.symbol} presente nella Restricted / Sanctions List aziendale.")
            status = ComplianceStatus.REJECTED_RESTRICTED_SYMBOL

        # 2. Controllo Fat-Finger Notional Limit
        if notional_eur > self.config.max_notional_per_order_eur:
            rejection_reasons.append(
                f"Nozionale ordine (€{notional_eur:,.2f}) supera il Fat-Finger Ceiling (€{self.config.max_notional_per_order_eur:,.2f})."
            )
            if status == ComplianceStatus.APPROVED:
                status = ComplianceStatus.REJECTED_FAT_FINGER

        # 3. Controllo Price Collar (Discostamento rispetto al Reference Price)
        if order.order_type.upper() == "LIMIT" and order.limit_price > 0 and ref_px > 0:
            price_dev_pct = abs(order.limit_price - ref_px) / ref_px * 100.0
            if price_dev_pct > self.config.max_price_collar_pct:
                rejection_reasons.append(
                    f"Prezzo limite (€{order.limit_price:,.2f}) devia del {price_dev_pct:.2f}% dal prezzo di mercato (€{ref_px:,.2f}), "
                    f"eccedendo il price collar massimo ammesso (+/-{self.config.max_price_collar_pct:.1f}%)."
                )
                if status == ComplianceStatus.APPROVED:
                    status = ComplianceStatus.REJECTED_COLLAR_BREACH
            elif price_dev_pct > (self.config.max_price_collar_pct * 0.7):
                warnings.append(
                    f"Prezzo limite prossimo alla soglia di collar ({price_dev_pct:.2f}% di scostamento rispetto a +/-{self.config.max_price_collar_pct:.1f}%)."
                )

        # 4. Controllo Partecipazione al Volume (ADV Slicing Gate)
        if order.adv_shares and order.adv_shares > 0:
            adv_part_pct = (abs(order.order_qty) / order.adv_shares) * 100.0
            if adv_part_pct > self.config.max_adv_participation_pct:
                rejection_reasons.append(
                    f"Quantità ordine ({order.order_qty:,.0f} azioni) rappresenta il {adv_part_pct:.2f}% dell'ADV "
                    f"({order.adv_shares:,.0f} azioni), superando il limite istituzionale del {self.config.max_adv_participation_pct:.1f}%."
                )
                if status == ComplianceStatus.APPROVED:
                    status = ComplianceStatus.REJECTED_ADV_LIMIT
            elif adv_part_pct > (self.config.max_adv_participation_pct * 0.8):
                warnings.append(
                    f"Attenzione: partecipazione elevata all'ADV ({adv_part_pct:.2f}%). Si consiglia l'utilizzo di algoritmi TWAP o VWAP."
                )

        # 5. Controllo Copertura Liquidità (Cash Sufficiency)
        cash_avail = order.available_cash_eur if order.available_cash_eur is not None else portfolio_cash
        if self.config.enforce_cash_coverage and order.side.upper() == "BUY" and cash_avail is not None:
            required_cash = notional_eur * (1.0 + self.config.cash_buffer_pct / 100.0)
            if required_cash > cash_avail:
                shortfall = required_cash - cash_avail
                rejection_reasons.append(
                    f"Liquidità disponibile insufficiente: richiesti €{required_cash:,.2f} (incluso buffer {self.config.cash_buffer_pct}%), "
                    f"disponibili €{cash_avail:,.2f}. Shortfall: €{shortfall:,.2f}."
                )
                if status == ComplianceStatus.APPROVED:
                    status = ComplianceStatus.REJECTED_INSUFFICIENT_FUNDS

        passed = len(rejection_reasons) == 0
        if passed and len(warnings) > 0:
            status = ComplianceStatus.WARNING

        # Calcolo audit hash immutabile SHA-256
        raw_payload = f"{order.order_id}|{order.symbol}|{order.side}|{order.order_qty}|{exec_px}|{status.value}|{passed}"
        audit_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

        verdict = ComplianceVerdict(
            order_id=order.order_id,
            symbol=order.symbol,
            status=status,
            passed=passed,
            notional_eur=round(notional_eur, 2),
            rejection_reasons=rejection_reasons,
            warnings=warnings,
            audit_hash=audit_hash,
        )

        self._audit_log.append(verdict)
        return verdict

    def evaluate_batch(
        self,
        orders: List[PreTradeOrderRequest],
        portfolio_cash: Optional[float] = None,
    ) -> List[ComplianceVerdict]:
        """Valuta una sequenza di ordini aggiornando la liquidità residua in caso di ordini BUY multipli."""
        results = []
        running_cash = portfolio_cash
        for ord_req in orders:
            verd = self.evaluate_order(ord_req, portfolio_cash=running_cash)
            results.append(verd)
            if verd.passed and ord_req.side.upper() == "BUY" and running_cash is not None:
                running_cash = max(0.0, running_cash - verd.notional_eur)
        return results

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Restituisce il log immutabile di tutti i verdetti emessi."""
        return [v.to_dict() for v in self._audit_log]

    def clear_audit_trail(self) -> None:
        """Svuota la cache audit locale."""
        self._audit_log.clear()
