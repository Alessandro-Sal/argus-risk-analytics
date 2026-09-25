"""1-Click Executive CRO & Investment Committee Board-Pack Generator Engine.

Synthesizes live risk, capital, liquidity, derivatives, ALM, and wealth telemetry across
the entire ARGUS v9.17.0 platform into:
1. Structured Committee Dossier JSON
2. Automated Chief Risk Officer (CRO) Prescriptive Action Checklist (Priority 1/2/3)
3. Self-contained, printable Executive HTML5 Committee Board-Pack Dossier
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.alm_ldi_engine import compute_alm_ldi_immunization
from core.ccar_stress_engine import compute_ccar_capital_stress
from core.isda_simm_engine import compute_isda_simm_margin
from core.ux_institutional_hub import APP_VERSION, compute_executive_traffic_light_radar


class ExecutiveBoardPackEngine:
    """Institutional CRO & Investment Committee Board-Pack Synthesizer."""

    def __init__(
        self,
        portfolio_name: str = "Argus Institutional Master Mandate",
        nav_eur: float = 125_000_000.0,
    ) -> None:
        self.portfolio_name = portfolio_name
        self.nav_eur = nav_eur

    def generate_board_pack(self) -> dict[str, Any]:
        """Synthesize multi-engine telemetry, CRO prescriptions, and HTML5 Board Pack."""
        radar = compute_executive_traffic_light_radar()
        simm = compute_isda_simm_margin()
        alm = compute_alm_ldi_immunization(asset_portfolio_eur=self.nav_eur)
        ccar = compute_ccar_capital_stress()

        sev_cet1 = float(ccar["severely_adverse_min_cet1_pct"])
        funding_ratio = float(alm["funding_ratio_pct"])
        simm_im = float(simm["total_simm_initial_margin_eur"])

        prescriptions: list[dict[str, str]] = [
            {
                "priority": "PRIORITY 1 - LDI & DURATION HEDGE",
                "domain": "Asset-Liability Management (ALM)",
                "action": (
                    f"Eseguire Receiver IRS 20Y per € {alm['required_20y_receiver_swap_notional_eur']:,.0f} "
                    f"per chiudere il Duration Gap ({alm['duration_gap_years']:+.2f} anni) e portare il Liability Hedge Ratio al 100%."
                ),
            },
            {
                "priority": "PRIORITY 2 - OTC MARGIN & CENTRAL CLEARING",
                "domain": "ISDA SIMM v2.6 & UMR",
                "action": (
                    f"Margine Iniziale ISDA SIMM pari a € {simm_im:,.0f} ({simm['umr_utilization_pct']:.1f}% della soglia UMR €50M). "
                    f"Il clearing su CCP LCH/Eurex riduce l'MVA annuo di € {simm['annual_ccp_mva_savings_eur']:,.0f}."
                ),
            },
            {
                "priority": "PRIORITY 3 - SUPERVISORY CAPITAL BUFFER",
                "domain": "Fed CCAR / EBA 9Q Stress",
                "action": (
                    f"Minimo CET1 nello scenario Severely Adverse pari a {sev_cet1:.2f}% (Trough in {ccar['severely_adverse_trough_quarter']}). "
                    f"Mantenere uno Stress Capital Buffer (SCB) prudenziale di almeno {ccar['required_stress_capital_buffer_scb_pct']:.2f}%."
                ),
            },
        ]

        as_of = datetime.now().strftime("%Y-%m-%d %H:%M")
        html_report = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8"/>
<title>ARGUS v{APP_VERSION} — Executive CRO & Investment Committee Board-Pack</title>
<style>
  body {{ font-family: 'Segoe UI', Roboto, sans-serif; background: #0b0f19; color: #f8fafc; margin: 28px; }}
  .header {{ background: linear-gradient(135deg, #1e293b, #0f172a); border-left: 5px solid #6366f1; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; }}
  .card {{ background: #161f30; border: 1px solid rgba(255,255,255,0.08); padding: 14px; border-radius: 8px; }}
  .kpi-title {{ font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700; }}
  .kpi-val {{ font-size: 20px; font-weight: 800; color: #10b981; margin-top: 4px; }}
  .rx {{ background: #161f30; border-left: 4px solid #f59e0b; padding: 12px 16px; margin-bottom: 10px; border-radius: 6px; }}
</style>
</head>
<body>
  <div class="header">
    <h2 style="margin:0;">🏛️ ARGUS v{APP_VERSION} — Executive CRO & Investment Committee Board-Pack</h2>
    <p style="margin:6px 0 0 0; color:#94a3b8;">Mandato: <b>{self.portfolio_name}</b> &bull; Generato il: {as_of} &bull; Stato Regolamentare: <b>{radar['overall_status']}</b></p>
  </div>
  <div class="grid">
    <div class="card"><div class="kpi-title">Consolidated NAV</div><div class="kpi-val">€ {self.nav_eur:,.0f}</div></div>
    <div class="card"><div class="kpi-title">ALM Funding Ratio</div><div class="kpi-val">{funding_ratio:.1f}%</div></div>
    <div class="card"><div class="kpi-title">ISDA SIMM Initial Margin</div><div class="kpi-val">€ {simm_im:,.0f}</div></div>
    <div class="card"><div class="kpi-title">CCAR Severely Adverse CET1</div><div class="kpi-val">{sev_cet1:.2f}%</div></div>
  </div>
  <h3>📋 Chief Risk Officer (CRO) Prescriptive Action Checklist</h3>
  {''.join([f'<div class="rx"><b>{p["priority"]} [{p["domain"]}]</b><br/>{p["action"]}</div>' for p in prescriptions])}
</body>
</html>"""

        return {
            "app_version": APP_VERSION,
            "portfolio_name": self.portfolio_name,
            "generated_at": as_of,
            "nav_eur": round(self.nav_eur, 2),
            "overall_regulatory_status": radar["overall_status"],
            "executive_kpis": {
                "alm_funding_ratio_pct": funding_ratio,
                "alm_surplus_eur": alm["accounting_surplus_eur"],
                "isda_simm_im_eur": simm_im,
                "ccp_mva_savings_eur": simm["annual_ccp_mva_savings_eur"],
                "ccar_severely_adverse_min_cet1_pct": sev_cet1,
                "ccar_required_scb_pct": ccar["required_stress_capital_buffer_scb_pct"],
            },
            "cro_prescriptions": prescriptions,
            "board_pack_html": html_report,
        }


def generate_executive_board_pack(
    portfolio_name: str = "Argus Institutional Master Mandate",
    nav_eur: float = 125_000_000.0,
) -> dict[str, Any]:
    """Convenience entrypoint for API and Streamlit UI integration."""
    engine = ExecutiveBoardPackEngine(portfolio_name=portfolio_name, nav_eur=nav_eur)
    return engine.generate_board_pack()
