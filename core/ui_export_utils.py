"""
==============================================================================
ARGUS FINANCIAL DATA EXPORT FRAMEWORK (core/ui_export_utils.py)
==============================================================================
Modulo universale di esportazione dati tabulari per l'intera piattaforma ARGUS
(Risk Analytics & Wealth Management).

Caratteristiche:
- CSV istituzionale con codifica UTF-8-SIG (BOM) per perfetta leggibilità in Microsoft Excel.
- Excel (.xlsx) professionale: generato in-memory con openpyxl (fallback xlsxwriter),
  testata Obsidian & Amber, formattazione numerica automatica (valute, percentuali, date),
  griglia contabile esplicita, blocco intestazione e auto-fit delle colonne.
- Caching delle serializzazioni binarie con @st.cache_data per zero-lag sui re-run.
- Nomi file dinamici intelligenti con timestamp e contesto portafoglio.
- Componenti UI Streamlit:
  * render_export_toolbar: micro-popover compatto senza consumo di spazio verticale.
  * render_table_with_export: wrapper unificato con card header, badge e data grid.
==============================================================================
"""

import io
import re
import datetime
from typing import Optional, Dict, Tuple, Any, List, Union
import streamlit as st
import pandas as pd
import numpy as np

# Verifica disponibilità motori Excel
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    import xlsxwriter
    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False


# ==============================================================================
# 1. SANITIZZAZIONE E PREPARAZIONE DATAFRAME
# ==============================================================================

def prepare_dataframe_for_export(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """
    Sanitizza e prepara un DataFrame per l'esportazione:
    - Restituisce un DataFrame vuoto se None.
    - Appiattisce colonne MultiIndex (unite con '_').
    - Ripristina l'indice come colonna se è un MultiIndex o ha un nome esplicito.
    - Converte tipi complessi/oggetti nested in stringhe sicure.
    """
    if df is None:
        return pd.DataFrame()

    if not isinstance(df, pd.DataFrame):
        try:
            df = pd.DataFrame(df)
        except Exception:
            return pd.DataFrame()

    if df.empty:
        return df.copy()

    df_clean = df.copy()

    # Appiattimento colonne MultiIndex
    if isinstance(df_clean.columns, pd.MultiIndex):
        flat_cols = []
        for col in df_clean.columns.values:
            parts = [str(c).strip() for c in col if str(c).strip() and not str(c).startswith("Unnamed")]
            flat_cols.append("_".join(parts) if parts else "Colonna")
        df_clean.columns = flat_cols

    # Appiattimento indice se rilevante (es. serie temporali o MultiIndex)
    if isinstance(df_clean.index, pd.MultiIndex):
        df_clean = df_clean.reset_index()
    elif df_clean.index.name is not None:
        # Se l'indice ha un nome (es. 'Date', 'Ticker'), trasformalo in colonna esportabile
        df_clean = df_clean.reset_index()

    # Normalizzazione tipi complessi per evitare crash di serializzazione Excel/CSV
    for col in df_clean.columns:
        if df_clean[col].dtype == object:
            # Se contiene dict o list, serializza a stringa
            sample_val = df_clean[col].dropna().iloc[0] if not df_clean[col].dropna().empty else None
            if isinstance(sample_val, (dict, list, set, tuple)):
                df_clean[col] = df_clean[col].apply(lambda x: str(x) if x is not None else "")

    return df_clean


def generate_export_filename(
    prefix: str = "argus_export",
    portfolio_name: Optional[str] = None,
    extension: str = "csv"
) -> str:
    """
    Genera un nome file dinamico contestuale conforme allo standard ARGUS:
    {prefisso}_{nome_portafoglio}_{YYYYMMDD_HHMMSS}.{ext}
    """
    clean_prefix = re.sub(r'[^\w\-]', '_', str(prefix or 'argus_export').strip()).strip('_')
    
    if not portfolio_name:
        portfolio_name = (
            st.session_state.get("portfolio_name")
            or st.session_state.get("wealth_active_portfolio_name")
            or st.session_state.get("selected_portfolio")
            or ""
        )
    
    clean_port = re.sub(r'[^\w\-]', '_', str(portfolio_name).strip()).strip('_')
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    parts = [clean_prefix]
    if clean_port and clean_port.lower() not in ("portfolio", "none", "nan"):
        parts.append(clean_port)
    parts.append(ts)

    base = "_".join(parts)
    ext = extension.lstrip('.')
    return f"{base}.{ext}"


# ==============================================================================
# 2. SERIALIZZATORI IN-MEMORY (CSV & EXCEL)
# ==============================================================================

def to_csv_bytes(
    df: pd.DataFrame,
    sep: str = ",",
    decimal: str = ".",
    encoding: str = "utf-8-sig"
) -> bytes:
    """
    Esporta un DataFrame in formato CSV in-memory.
    Utilizza di default codifica UTF-8 con BOM (utf-8-sig) per garantire che
    Microsoft Excel su Windows e Mac apra il file interpretando correttamente
    caratteri speciali, simboli di valuta (€) e lettere accentate.
    """
    clean_df = prepare_dataframe_for_export(df)
    if clean_df.empty:
        return b""

    # to_csv con encoding utf-8-sig restituisce stringa codificabile in bytes
    csv_str = clean_df.to_csv(index=False, sep=sep, decimal=decimal)
    return csv_str.encode(encoding)


def to_excel_bytes(
    df: pd.DataFrame,
    sheet_name: str = "Dati",
    table_title: Optional[str] = None,
    base_currency: str = "EUR"
) -> bytes:
    """
    Esporta un DataFrame in un file Microsoft Excel (.xlsx) professionale:
    - Header stilizzato Obsidian Dark (#161B22) con testo in grassetto bianco (#FFFFFF)
      e linea di accento ambra (#FF9900).
    - Griglia contabile attiva e visibile (showGridLines = True).
    - Formattazione numerica automatica (valute, percentuali, date, interi).
    - Freeze Panes della prima riga (blocco intestazione durante lo scroll).
    - Auto-adattamento della larghezza delle colonne con margine protettivo.
    """
    clean_df = prepare_dataframe_for_export(df)
    if clean_df.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl" if HAS_OPENPYXL else "xlsxwriter") as writer:
            pd.DataFrame({"Messaggio": ["Nessun dato disponibile"]}).to_excel(writer, index=False, sheet_name=sheet_name[:31])
        return output.getvalue()

    output = io.BytesIO()

    # Motore 1: openpyxl (massima flessibilità stilistica istituzionale)
    if HAS_OPENPYXL:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_name[:31] if sheet_name else "Dati"

        # Abilita sempre le linee della griglia (Excel le nasconde se ci sono fill)
        ws.views.sheetView[0].showGridLines = True

        # Palette & Stili ARGUS Obsidian
        header_fill = PatternFill(start_color="161B22", end_color="161B22", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_align = Alignment(horizontal="center", vertical="center", wrap_text=False)
        header_border = Border(
            bottom=Side(style='medium', color="FF9900"),
            left=Side(style='thin', color="30363D"),
            right=Side(style='thin', color="30363D"),
            top=Side(style='thin', color="30363D")
        )

        data_font = Font(name="Calibri", size=10, color="1F2328")
        data_border = Border(
            left=Side(style='thin', color="E1E4E8"),
            right=Side(style='thin', color="E1E4E8"),
            top=Side(style='thin', color="E1E4E8"),
            bottom=Side(style='thin', color="E1E4E8")
        )
        zebra_fill = PatternFill(start_color="F6F8FA", end_color="F6F8FA", fill_type="solid")

        # Scrittura intestazione (riga 1)
        headers = [str(col) for col in clean_df.columns]
        ws.append(headers)

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_align
            cell.border = header_border

        # Rilevamento formati per colonna
        curr_symbol = "€" if base_currency == "EUR" else ("$" if base_currency == "USD" else base_currency)
        col_formats: Dict[int, str] = {}

        for col_idx, col_name in enumerate(clean_df.columns, 1):
            name_lower = str(col_name).lower()
            col_series = clean_df[col_name].dropna()

            # 1. Valuta
            if any(k in name_lower for k in ("€", "$", "£", "valore", "prezzo", "controvalore", "costo", "pnl", "nav", "cash", "patrimonio", "spesa", "ricavo", "amount", "capital", "wacp")):
                col_formats[col_idx] = f'#,##0.00 "{curr_symbol}"'
            # 2. Percentuale
            elif any(k in name_lower for k in ("%", "pct", "peso", "weight", "rendimento", "yield", "rate", "drawdown", "volatilit", "var", "cvar")):
                if not col_series.empty and pd.api.types.is_numeric_dtype(col_series):
                    max_abs = col_series.abs().max()
                    col_formats[col_idx] = '0.00"%"' if max_abs > 1.5 else '0.00%'
                else:
                    col_formats[col_idx] = '0.00"%"'
            # 3. Date / Datetime
            elif pd.api.types.is_datetime64_any_dtype(clean_df[col_name]) or any(k in name_lower for k in ("data", "date", "timestamp")):
                col_formats[col_idx] = 'yyyy-mm-dd'
            # 4. Numeri interi generici
            elif pd.api.types.is_integer_dtype(clean_df[col_name]):
                col_formats[col_idx] = '#,##0'
            # 5. Numeri decimali generici
            elif pd.api.types.is_float_dtype(clean_df[col_name]):
                col_formats[col_idx] = '#,##0.00'

        # Scrittura righe dati
        for row_idx, row_data in enumerate(clean_df.itertuples(index=False), 2):
            is_even = (row_idx % 2 == 0)
            for col_idx, val in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col_idx)

                # Gestione NaN / None
                if pd.isna(val):
                    cell.value = ""
                elif isinstance(val, (datetime.date, datetime.datetime)):
                    cell.value = val
                elif isinstance(val, (np.integer, int)):
                    cell.value = int(val)
                elif isinstance(val, (np.floating, float)):
                    cell.value = float(val)
                else:
                    cell.value = str(val)

                cell.font = data_font
                cell.border = data_border
                if is_even:
                    cell.fill = zebra_fill

                # Applicazione formato numerico
                if col_idx in col_formats and isinstance(cell.value, (int, float, datetime.date, datetime.datetime)):
                    cell.number_format = col_formats[col_idx]

        # Blocco riga intestazione
        ws.freeze_panes = "A2"

        # Auto-fit larghezza colonne
        for col_idx in range(1, len(headers) + 1):
            col_letter = get_column_letter(col_idx)
            max_len = len(headers[col_idx - 1])
            for row_idx in range(2, min(ws.max_row + 1, 202)):
                c_val = ws.cell(row=row_idx, column=col_idx).value
                if c_val is not None:
                    max_len = max(max_len, len(str(c_val)))
            ws.column_dimensions[col_letter].width = max(min(max_len + 4, 50), 12)

        wb.save(output)
        return output.getvalue()

    # Fallback con xlsxwriter
    elif HAS_XLSXWRITER:
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            clean_df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
            workbook = writer.book
            worksheet = writer.sheets[sheet_name[:31]]

            header_format = workbook.add_format({
                'bold': True,
                'font_color': '#FFFFFF',
                'bg_color': '#161B22',
                'border': 1,
                'border_color': '#30363D',
                'align': 'center'
            })
            for col_num, value in enumerate(clean_df.columns.values):
                worksheet.write(0, col_num, str(value), header_format)
                col_len = max(len(str(value)), clean_df[value].astype(str).map(len).max() if not clean_df.empty else 0)
                worksheet.set_column(col_num, col_num, max(min(col_len + 4, 50), 12))

        return output.getvalue()

    # Fallback estremo senza librerie aggiuntive
    else:
        clean_df.to_excel(output, index=False, sheet_name=sheet_name[:31])
        return output.getvalue()


# ==============================================================================
# 3. PERFORMANCE & STREAMLIT DATA CACHING
# ==============================================================================

@st.cache_data(show_spinner=False)
def get_cached_csv_bytes(df: pd.DataFrame, sep: str = ",") -> bytes:
    """Funzione con cache per serializzazione CSV ultra-rapida."""
    return to_csv_bytes(df, sep=sep)


@st.cache_data(show_spinner=False)
def get_cached_excel_bytes(
    df: pd.DataFrame,
    sheet_name: str = "Dati",
    base_currency: str = "EUR"
) -> bytes:
    """Funzione con cache per serializzazione Excel professionale."""
    return to_excel_bytes(df, sheet_name=sheet_name, base_currency=base_currency)


# ==============================================================================
# 4. COMPONENTI UI STREAMLIT (TOOLBAR & TABLE WRAPPER)
# ==============================================================================

def render_export_toolbar(
    df: pd.DataFrame,
    file_prefix: str = "export",
    key_suffix: str = "main",
    table_title: Optional[str] = None,
    sheet_name: str = "Dati",
    show_row_count: bool = True
) -> None:
    """
    Renderizza un micro-popover compatto '📥 Esporta Dati' progettato per
    integrarsi perfettamente nelle toolbar delle card senza ingombro verticale.
    
    Contiene:
    - Badge con il conteggio di righe e colonne.
    - Download button per Excel (.xlsx) professionale formattato.
    - Download button per CSV compatibile con Excel italiano (UTF-8 SIG).
    """
    if df is None or df.empty:
        st.caption("*(Nessun dato esportabile)*")
        return

    n_rows, n_cols = df.shape
    curr = st.session_state.get("base_currency", "EUR")

    csv_filename = generate_export_filename(file_prefix, extension="csv")
    xlsx_filename = generate_export_filename(file_prefix, extension="xlsx")

    # Micro Popover Elegante
    popover_label = "📥 Esporta"
    popover_help = f"Esporta {n_rows:,} record in formato Excel professionale (.xlsx) o CSV"

    with st.popover(popover_label, help=popover_help, use_container_width=False):
        st.markdown(
            f"""
            <div style="font-size: 0.82rem; font-weight: 600; color: #8b949e; margin-bottom: 8px;">
                OPZIONI DI ESPORTAZIONE DATI
            </div>
            """,
            unsafe_allow_html=True
        )

        if show_row_count:
            st.markdown(
                f"""
                <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(255,153,0,0.1); border: 1px solid rgba(255,153,0,0.3); border-radius: 6px; padding: 3px 8px; margin-bottom: 12px; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #ff9900;">
                    <span>📊</span>
                    <span><b>{n_rows:,}</b> righe • <b>{n_cols}</b> colonne</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Generazione binarie lazy/cached
        excel_data = get_cached_excel_bytes(df, sheet_name=sheet_name, base_currency=curr)
        csv_data = get_cached_csv_bytes(df, sep=",")

        # 1. Download Excel
        st.download_button(
            label="📊 Scarica Excel (.xlsx)",
            data=excel_data,
            file_name=xlsx_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"dl_xlsx_{file_prefix}_{key_suffix}",
            help="File Microsoft Excel formattato con colori istituzionali, griglia contabile e formati numerici automatici."
        )

        # 2. Download CSV (UTF-8 con BOM)
        st.download_button(
            label="📄 Scarica CSV (Excel IT/EU)",
            data=csv_data,
            file_name=csv_filename,
            mime="text/csv",
            use_container_width=True,
            key=f"dl_csv_{file_prefix}_{key_suffix}",
            help="File CSV con codifica UTF-8 BOM per apertura immediata senza anomalie di caratteri speciali in Excel europeo."
        )


def render_table_with_export(
    df: pd.DataFrame,
    table_title: Optional[str] = None,
    file_prefix: str = "tabella",
    key_suffix: str = "tbl",
    column_config: Optional[Dict[str, Any]] = None,
    currency_cols: Optional[List[str]] = None,
    pct_cols: Optional[List[str]] = None,
    progress_cols: Optional[Dict[str, Tuple[float, float]]] = None,
    hide_index: bool = True,
    height: Optional[int] = 380,
    sheet_name: str = "Dati"
) -> None:
    """
    Wrapper universale All-in-One per visualizzare un DataFrame con design
    istituzionale ARGUS e toolbar di esportazione integrata.
    
    Layout:
    ┌───────────────────────────────────────────────────────────┐
    │ 📋 Titolo Tabella   [ 42 righe • 8 col ]      [📥 Esporta]│
    ├───────────────────────────────────────────────────────────┤
    │ (st.dataframe con formattazione e progress columns)      │
    └───────────────────────────────────────────────────────────┘
    """
    if df is None or df.empty:
        if table_title:
            st.markdown(f"##### {table_title}")
        st.info("Nessun record disponibile nella tabella.")
        return

    # Header Bar con Titolo a sinistra e Toolbar Export a destra
    col_title, col_export = st.columns([0.82, 0.18], gap="small")
    
    with col_title:
        if table_title:
            st.markdown(
                f"""
                <div style="display: flex; align-items: baseline; gap: 10px; margin-top: 2px;">
                    <span style="font-size: 1.05rem; font-weight: 700; color: #ffffff; letter-spacing: -0.2px;">
                        {table_title}
                    </span>
                    <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.76rem; color: #8b949e; background: rgba(255,255,255,0.06); padding: 1px 7px; border-radius: 4px;">
                        {len(df):,} righe
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #8b949e; margin-top: 4px;">
                    {len(df):,} record disponibili
                </div>
                """,
                unsafe_allow_html=True
            )

    with col_export:
        render_export_toolbar(
            df=df,
            file_prefix=file_prefix,
            key_suffix=key_suffix,
            table_title=table_title,
            sheet_name=sheet_name,
            show_row_count=False  # Già visibile nel titolo
        )

    # Configurazione automatica colonne se passati elenchi semplificati
    cfg = column_config.copy() if column_config else {}
    base_curr = st.session_state.get("base_currency", "EUR")
    curr_symbol = "€" if base_curr == "EUR" else ("$" if base_curr == "USD" else base_curr)

    if currency_cols:
        for c in currency_cols:
            if c in df.columns and c not in cfg:
                cfg[c] = st.column_config.NumberColumn(
                    c,
                    format=f"{curr_symbol} %.2f",
                    help=f"Importo espresso in {base_curr}"
                )

    if pct_cols:
        for c in pct_cols:
            if c in df.columns and c not in cfg:
                cfg[c] = st.column_config.NumberColumn(
                    c,
                    format="%.2f%%",
                    help="Valore percentuale"
                )

    if progress_cols:
        for c, (min_v, max_v) in progress_cols.items():
            if c in df.columns and c not in cfg:
                cfg[c] = st.column_config.ProgressColumn(
                    c,
                    min_value=min_v,
                    max_value=max_v,
                    format="%.1f%%" if max_v <= 100 and min_v >= 0 else "%.2f",
                    help=f"Allocazione / Intensità per {c}"
                )

    # Render data grid
    st.dataframe(
        df,
        column_config=cfg if cfg else None,
        hide_index=hide_index,
        height=height,
        use_container_width=True
    )
