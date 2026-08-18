import os
import io
import pandas as pd
import numpy as np
from datetime import datetime

# ReportLab imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

from core.html_exporter import generate_html_report_bytes, generate_interactive_html_report


def generate_pdf_factsheet(results: dict, portfolio_name: str = "My Portfolio") -> bytes:
    """
    Genera un Report PDF Executive Factsheet a 2 pagine in-memory.
    Ritorna il buffer di byte PDF pronti per il download Streamlit.
    """
    if not HAS_REPORTLAB:
        raise ImportError("Le librerie reportlab non sono installate.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A')
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B')
    )
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=6
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#334155')
    )
    cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#0F172A')
    )

    story = []

    # ── Header Banner ───────────────────────────────────────
    story.append(Paragraph(f"<b>ARGUS QUANTITATIVE FACTSHEET</b> — {portfolio_name.upper()}", title_style))
    story.append(Paragraph(f"Data Report: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Benchmark: {results.get('metrics', {}).get('market_risk', {}).get('benchmark_ticker', 'SPY')}", subtitle_style))
    story.append(Spacer(1, 12))

    # ── Key Metrics Summary Table ────────────────────────────
    m = results.get("metrics", {})
    ret = m.get("returns", {})
    mk = m.get("market_risk", {})
    con = m.get("concentration", {})

    kpi_data = [
        [
            Paragraph("Valore Portafoglio", cell_bold), Paragraph(f"€ {ret.get('portfolio_value', 0):,.2f}", cell_style),
            Paragraph("CAGR Annuo", cell_bold), Paragraph(f"{ret.get('cagr_pct', 0):+.2f}%", cell_style)
        ],
        [
            Paragraph("PnL Cumulato", cell_bold), Paragraph(f"€ {ret.get('total_pnl', 0):,.2f}", cell_style),
            Paragraph("Sharpe Ratio", cell_bold), Paragraph(f"{ret.get('sharpe_ratio', 0):.2f}", cell_style)
        ],
        [
            Paragraph("Value at Risk (VaR 95%)", cell_bold), Paragraph(f"€ {mk.get('var_95', 0):,.2f}", cell_style),
            Paragraph("Max Drawdown", cell_bold), Paragraph(f"{mk.get('max_drawdown_pct', 0):.2f}%", cell_style)
        ],
        [
            Paragraph("Beta vs Benchmark", cell_bold), Paragraph(f"{mk.get('beta', 1.0):.2f}", cell_style),
            Paragraph("HHI Concentrazione", cell_bold), Paragraph(f"{con.get('hhi', 0):.4f}", cell_style)
        ]
    ]

    t_kpi = Table(kpi_data, colWidths=[130, 135, 130, 135])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 15))

    # ── Asset Allocation & Top Holdings ───────────────────────
    story.append(Paragraph("Dettaglio Top Posizioni in Portafoglio", h2_style))
    
    pos = results.get("positions", pd.DataFrame())
    if not pos.empty:
        top_pos = pos.sort_values(by="current_value", ascending=False).head(10)
        pos_table_data = [[
            Paragraph("Ticker", cell_bold), Paragraph("Classe", cell_bold), 
            Paragraph("Quantità", cell_bold), Paragraph("Prezzo", cell_bold), 
            Paragraph("Valore (€)", cell_bold), Paragraph("Peso %", cell_bold)
        ]]
        
        for _, r in top_pos.iterrows():
            pos_table_data.append([
                Paragraph(str(r.get("ticker")), cell_style),
                Paragraph(str(r.get("asset_class", "Stock")), cell_style),
                Paragraph(f"{r.get('qty_net', 0):,.2f}", cell_style),
                Paragraph(f"€ {r.get('last_price', 0):,.2f}", cell_style),
                Paragraph(f"€ {r.get('current_value', 0):,.2f}", cell_style),
                Paragraph(f"{r.get('weight_pct', 0):.2f}%", cell_style),
            ])

        t_pos = Table(pos_table_data, colWidths=[75, 85, 80, 95, 105, 90])
        t_pos.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_pos)

    story.append(Spacer(1, 15))

    # ── Stress Testing Summary ───────────────────────────────
    story.append(Paragraph("Valutazione degli Scenario Stress Test", h2_style))
    stress_tests = results.get("stress_tests", {})
    
    if stress_tests:
        stress_data = [[
            Paragraph("Scenario Storico", cell_bold), 
            Paragraph("Shock Mkt", cell_bold), 
            Paragraph("Perdita Stimata (€)", cell_bold), 
            Paragraph("Perdita Stimata (%)", cell_bold)
        ]]
        for name, st_info in stress_tests.items():
            stress_data.append([
                Paragraph(name, cell_style),
                Paragraph(f"{st_info.get('benchmark_shock_pct', 0):+.1f}%", cell_style),
                Paragraph(f"€ {st_info.get('portfolio_loss_eur', 0):,.2f}", cell_style),
                Paragraph(f"{st_info.get('portfolio_loss_pct', 0):+.2f}%", cell_style),
            ])
            
        t_stress = Table(stress_data, colWidths=[180, 90, 130, 130])
        t_stress.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_stress)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_excel_report(results: dict, portfolio_name: str = "My Portfolio") -> bytes:
    """
    Genera un Excel Workbook (.xlsx) multi-tab in-memory.
    Ritorna i byte pronti per il download in Streamlit.
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Tab 1: Executive Summary
        m = results.get("metrics", {})
        ret = m.get("returns", {})
        mk = m.get("market_risk", {})
        con = m.get("concentration", {})

        summary_rows = [
            {"Metrica": "Nome Portafoglio", "Valore": portfolio_name},
            {"Metrica": "Data Calcolo", "Valore": results.get("computed_at", datetime.now().strftime("%Y-%m-%d"))},
            {"Metrica": "Valore Totale (€)", "Valore": ret.get("portfolio_value", 0)},
            {"Metrica": "Capitale Investito (€)", "Valore": ret.get("cost_basis_total", 0)},
            {"Metrica": "PnL Cumulato (€)", "Valore": ret.get("total_pnl", 0)},
            {"Metrica": "CAGR (%)", "Valore": ret.get("cagr_pct", 0)},
            {"Metrica": "Sharpe Ratio", "Valore": ret.get("sharpe_ratio", 0)},
            {"Metrica": "Sortino Ratio", "Valore": ret.get("sortino_ratio", 0)},
            {"Metrica": "Volatilità Annua (%)", "Valore": mk.get("volatility_annual_pct", 0)},
            {"Metrica": "Value at Risk 95% (€)", "Valore": mk.get("var_95", 0)},
            {"Metrica": "Value at Risk 99% (€)", "Valore": mk.get("var_99", 0)},
            {"Metrica": "Max Drawdown (%)", "Valore": mk.get("max_drawdown_pct", 0)},
            {"Metrica": "Beta vs Benchmark", "Valore": mk.get("beta", 1.0)},
            {"Metrica": "Indice HHI Concentrazione", "Valore": con.get("hhi", 0)},
        ]
        df_summary = pd.DataFrame(summary_rows)
        df_summary.to_excel(writer, sheet_name="Executive Summary", index=False)

        # Tab 2: Posizioni & Dettagli
        pos = results.get("positions", pd.DataFrame())
        if not pos.empty:
            pos.to_excel(writer, sheet_name="Posizioni Dettaglio", index=False)

        # Tab 3: Rendimenti Giornalieri
        sr_port = results.get("portfolio_return", pd.Series())
        sr_bm = results.get("benchmark_return", pd.Series())
        if not sr_port.empty:
            sr_bm_aligned = sr_bm.reindex(sr_port.index).fillna(0.0) if not sr_bm.empty else pd.Series(0.0, index=sr_port.index)
            df_ret = pd.DataFrame({
                "Data": sr_port.index.strftime("%Y-%m-%d"),
                "Rendimento Portafoglio (%)": (sr_port.values * 100).round(4),
                "Rendimento Benchmark (%)": (sr_bm_aligned.values * 100).round(4),
            })
            df_ret.to_excel(writer, sheet_name="Rendimenti Storici", index=False)

        # Tab 4: Stress Tests
        stress = results.get("stress_tests", {})
        if stress:
            stress_rows = []
            for s_name, s_val in stress.items():
                stress_rows.append({
                    "Scenario": s_name,
                    "Shock Benchmark (%)": s_val.get("benchmark_shock_pct"),
                    "Perdita Stimata (€)": s_val.get("portfolio_loss_eur"),
                    "Perdita Stimata (%)": s_val.get("portfolio_loss_pct")
                })
            pd.DataFrame(stress_rows).to_excel(writer, sheet_name="Stress Testing", index=False)

    output.seek(0)
    return output.getvalue()

# Alias for backwards compatibility
generate_pdf_report = generate_pdf_factsheet
