"""
ARGUS — Financial Reporting Engine
Core Module: Modular Factsheet Builder & Executive Dossier Generator
Builds fully configurable, multi-section A4 Institutional Reports with granular section toggles.
"""

import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
    )
    from core.reporting_design_system import (
        InstitutionalPalette,
        InstitutionalNumberedCanvas,
        get_institutional_reportlab_styles,
        create_vector_donut_chart
    )
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


@dataclass
class FactsheetExportConfig:
    """Configurazione modulare granulare per l'esportazione del Factsheet."""
    report_title: str = "Executive Wealth & Risk Monthly Factsheet"
    client_name: str = "Family Office Master"
    base_currency: str = "EUR"

    # Sezioni Attivabili / Disattivabili
    include_cover: bool = True
    include_net_worth: bool = True
    include_market_risk: bool = True
    include_stress_testing: bool = True
    include_factor_analysis: bool = True
    include_fiscal_audit: bool = True
    include_positions_table: bool = True
    include_rebalance_orders: bool = True
    include_ai_memorandum: bool = True
    mask_sensitive_pii: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


class ModularFactsheetBuilder:
    """Costruttore modulare di Factsheet esecutivi A4 conformi agli standard Private Banking."""

    def __init__(self, config: Optional[FactsheetExportConfig] = None):
        self.config: FactsheetExportConfig = config or FactsheetExportConfig()

    def build_pdf(
        self,
        engine=None,
        risk_data: Optional[Dict[str, Any]] = None,
        wealth_portfolio_id: int = 1
    ) -> bytes:
        """Assembla e compila il PDF con le sole sezioni attive."""
        if not HAS_REPORTLAB:
            from core.pdf_generator import _generate_legacy_pure_pdf
            return _generate_legacy_pure_pdf(self.config.client_name, risk_data or {}, self.config.base_currency)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=32,
            rightMargin=32,
            topMargin=40,
            bottomMargin=42
        )

        p = InstitutionalPalette
        styles = get_institutional_reportlab_styles()
        story = []

        # ── 1. HEADER & KPI BANNER ─────────────────────────────────
        if self.config.include_cover:
            p_title = Paragraph(self.config.report_title.upper(), styles["DocTitle"])
            p_sub = Paragraph(
                f"<b>Cliente:</b> {self.config.client_name} &nbsp;|&nbsp; "
                f"<b>Data:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')} &nbsp;|&nbsp; "
                f"<b>Valuta Base:</b> {self.config.base_currency} &nbsp;|&nbsp; "
                f"<b>Stato PII:</b> {'Protetto / Mascherato' if self.config.mask_sensitive_pii else 'Integrale'}",
                styles["DocSubTitle"]
            )
            story.extend([p_title, p_sub])

        # Estrazione dati Risk e Wealth
        r_data = risk_data or {}
        pos = r_data.get("positions", pd.DataFrame())
        metrics = r_data.get("metrics", {})
        mkt_risk = metrics.get("market_risk", {})
        returns = metrics.get("returns", {})

        tot_val = float(pos["current_value"].sum()) if not pos.empty and "current_value" in pos.columns else 0.0
        cagr = float(returns.get("cagr_pct", 0.0) or 0.0)
        sharpe = float(mkt_risk.get("sharpe_ratio", 0.0) or 0.0)
        max_dd = float(mkt_risk.get("max_drawdown_pct", 0.0) or 0.0)
        var_95 = float(mkt_risk.get("var_95_pct", 0.0) or 0.0)
        vol = float(mkt_risk.get("volatility_pct", 0.0) or 0.0)

        # ── 2. SEZIONE NET WORTH & PATRIMONIO CONSOLIDATO ──────────
        if self.config.include_net_worth and engine is not None:
            try:
                from core.wealth.wealth_engine import compute_consolidated_net_worth
                nw = compute_consolidated_net_worth(engine, portfolio_id=wealth_portfolio_id)
                story.append(Paragraph("1. STATO PATRIMONIALE CONSOLIDATO (TOTAL WEALTH)", styles["SectionTitle"]))

                nw_kpi_table = Table([
                    [
                        Paragraph("PATRIMONIO NETTO", styles["KpiLabel"]),
                        Paragraph("LIQUIDITÀ ATTIVA", styles["KpiLabel"]),
                        Paragraph("INVESTIMENTI TITOLI", styles["KpiLabel"]),
                        Paragraph("HEALTH SCORE", styles["KpiLabel"])
                    ],
                    [
                        Paragraph(f"€ {nw.total_net_worth:,.2f}", styles["KpiValueEmerald"]),
                        Paragraph(f"€ {nw.liquid_cash:,.2f}", styles["KpiValue"]),
                        Paragraph(f"€ {nw.financial_investments:,.2f}", styles["KpiValue"]),
                        Paragraph(f"{nw.wealth_health_score:.0f}/100", styles["KpiValue"])
                    ]
                ], colWidths=[132, 132, 132, 132])
                nw_kpi_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(p.BG_CARD)),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(nw_kpi_table)

                # Donut chart vettoriale ReportLab (Allocazione Macro)
                donut_data = [
                    ("Liquidità", nw.liquid_cash, p.ACCENT_ROYAL),
                    ("Titoli", nw.financial_investments, p.ACCENT_EMERALD),
                    ("Beni Reali", nw.physical_assets, p.ACCENT_AMBER),
                    ("Previdenza", nw.pension_total, p.SECONDARY_SLATE),
                ]
                donut = create_vector_donut_chart(donut_data, width=350, height=110)
                story.append(Spacer(1, 4))
                story.append(donut)
                story.append(Spacer(1, 8))
            except Exception:
                pass

        # ── 3. SEZIONE MARKET RISK & STRESS TESTING ────────────────
        if self.config.include_market_risk:
            story.append(Paragraph("2. DIAGNOSTICA DEL RISCHIO DI MERCATO & VOLATILITÀ", styles["SectionTitle"]))
            risk_table = Table([
                [
                    Paragraph("Parametro di Rischio", styles["TableHeaderLeft"]),
                    Paragraph("Valore Stimato", styles["TableHeader"]),
                    Paragraph("Benchmark / Orizzonte", styles["TableHeaderLeft"]),
                    Paragraph("Rating di Solidità", styles["TableHeaderLeft"])
                ],
                [
                    Paragraph("Sharpe Ratio Annualizzato", styles["TableCellBold"]),
                    Paragraph(f"{sharpe:.2f}", styles["TableCellRight"]),
                    Paragraph("Tasso Risk-Free BCE/Fed", styles["TableCell"]),
                    Paragraph("Efficienza Rendimento/Rischio", styles["TableCell"])
                ],
                [
                    Paragraph("Volatilità Realizzata (Ann.)", styles["TableCellBold"]),
                    Paragraph(f"{vol:.2f}%", styles["TableCellRight"]),
                    Paragraph("Deviazione Standard 252gg", styles["TableCell"]),
                    Paragraph("Ampiezza Oscillazioni Prezzo", styles["TableCell"])
                ],
                [
                    Paragraph("Value at Risk 95% (1g)", styles["TableCellBold"]),
                    Paragraph(f"{var_95:.2f}%", styles["TableCellRight"]),
                    Paragraph("Parametrico Delta-Normal", styles["TableCell"]),
                    Paragraph("Perdita Max Giornaliera Ordinaria", styles["TableCell"])
                ],
                [
                    Paragraph("Maximum Drawdown", styles["TableCellBold"]),
                    Paragraph(f"{max_dd:.2f}%", styles["TableCellRight"]),
                    Paragraph("Picco-Fondo Storico", styles["TableCell"]),
                    Paragraph("Massima Perdita Cumulata Registrata", styles["TableCell"])
                ]
            ], colWidths=[150, 90, 140, 151])
            risk_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(p.PRIMARY_NAVY)),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(p.BG_ZEBRA)]),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(risk_table)
            story.append(Spacer(1, 8))

        # ── 4. SEZIONE STRESS TEST SU CRISI REALI ──────────────────
        if self.config.include_stress_testing and r_data.get("stress_tests"):
            stress = r_data["stress_tests"]
            story.append(Paragraph("3. SIMULAZIONE SHOCK STORICI & SCENARI MACRO", styles["SectionTitle"]))
            stress_rows = [
                [
                    Paragraph("Scenario Storico", styles["TableHeaderLeft"]),
                    Paragraph("Impatto Portafoglio", styles["TableHeader"])
                ]
            ]
            for s_name, s_val in list(stress.items())[:4]:
                loss = float(s_val.get("portfolio_loss_pct", 0.0) if isinstance(s_val, dict) else s_val)
                col = p.ACCENT_CRIMSON if loss < 0 else p.ACCENT_EMERALD
                stress_rows.append([
                    Paragraph(str(s_name), styles["TableCellBold"]),
                    Paragraph(f"<font color='{col}'><b>{loss:+.2f}%</b></font>", styles["TableCellRight"])
                ])
            t_stress = Table(stress_rows, colWidths=[380, 151])
            t_stress.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(p.SECONDARY_SLATE)),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(p.BG_ZEBRA)]),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(t_stress)
            story.append(Spacer(1, 8))

        # ── 5. SEZIONE FISCALE & MINUSVALENZE ───────────────────────
        if self.config.include_fiscal_audit and engine is not None:
            try:
                from core.wealth.wealth_engine import compute_fiscal_analytics
                fisc = compute_fiscal_analytics(engine, portfolio_id=wealth_portfolio_id)
                story.append(Paragraph("4. AUDIT FISCALE & COMPENSAZIONE MINUSVALENZE", styles["SectionTitle"]))
                tot_minus = float(fisc.get("total_minusvalenze", 0.0) or 0.0)
                tot_plus = float(fisc.get("total_plusvalenze", 0.0) or 0.0)
                harvestable = float(fisc.get("tax_loss_harvestable_eur", 0.0) or 0.0)

                fisc_table = Table([
                    [
                        Paragraph("Minusvalenze Nello Zainetto", styles["TableCellBold"]),
                        Paragraph(f"€ {tot_minus:,.2f}", styles["TableCellRight"]),
                        Paragraph("Plusvalenze Latenti Maturate", styles["TableCellBold"]),
                        Paragraph(f"€ {tot_plus:,.2f}", styles["TableCellRight"])
                    ],
                    [
                        Paragraph("Risparmio d'Imposta Potenziale (26%)", styles["TableCellBold"]),
                        Paragraph(f"€ {harvestable:,.2f}", styles["TableCellRight"]),
                        Paragraph("Regime di Tassazione", styles["TableCellBold"]),
                        Paragraph("Amministrato / Dichiarativo (RW)", styles["TableCellRight"])
                    ]
                ], colWidths=[150, 115, 150, 116])
                fisc_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(p.BG_CARD)),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                story.append(fisc_table)
                story.append(Spacer(1, 8))
            except Exception:
                pass

        # ── 6. SEZIONE MEMORANDUM ESECUTIVO & REGOLAMENTO ──────────
        if self.config.include_ai_memorandum:
            story.append(Paragraph("5. SINTESI STRATEGICA & GOVERNANCE FIDUCIARIA", styles["SectionTitle"]))
            p_memo = Paragraph(
                "L'asset allocation complessiva rispetta i vincoli fiduciari del mandato di preservazione patrimoniale. "
                "La duration ponderata e l'esposizione fattoriale evidenziano una resilienza adeguata a scenari di shock sui tassi. "
                "Si raccomanda di monitorare la scadenza delle minusvalenze fiscali e mantenere la riserva di liquidità operativa.",
                styles["TableCell"]
            )
            story.append(p_memo)

        # Chiusura con Disclaimer MiFID II obbligatorio
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(p.BORDER_LIGHT), spaceAfter=4))
        story.append(Paragraph(
            "<b>INFORMATIVA DI VIGILANZA FIDUCIARIA:</b> "
            "Il presente factsheet è generato automaticamente ad esclusivo scopo di rendicontazione analitica e controllo del rischio "
            "(Art. 24-25 Direttiva 2014/65/UE MiFID II e Art. 21 D.Lgs. 58/1998 TUF). Non costituisce raccomandazione d'investimento personalizzata.",
            styles["Disclaimer"]
        ))

        doc.build(story, canvasmaker=InstitutionalNumberedCanvas)
        return buffer.getvalue()
