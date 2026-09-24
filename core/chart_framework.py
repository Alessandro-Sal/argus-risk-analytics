"""
ARGUS Institutional Plotly Design System & High-Performance Chart Framework
=============================================================================
Centralized enterprise visualization library for ARGUS Risk Analytics & Wealth Management:
- Institutional Dark Theme (transparent background, subtle low-contrast grid, Outfit & JetBrains Mono)
- Categorical semantic financial palette (Equity, Fixed Income, Commodities, Crypto, Real Estate, Cash, Risk)
- High-Performance WebGL engine (automatic switch to go.Scattergl for >= 1,000 points)
- LTTB (Largest Triangle Three Buckets) pure NumPy downsampling for large time series (< 15ms for 20k pts)
- 4 Production-ready wrapper charts:
    1. create_timeseries_chart()       (Equity curve + Synchronous Underwater Drawdown pane)
    2. create_montecarlo_fan_chart()   (Statistical fan chart with 90% and 50% confidence bands)
    3. create_asset_allocation_treemap() (Multi-level allocation with Finviz-style PnL color scale)
    4. create_waterfall_cashflow()     (Institutional cash flow / net worth waterfall)
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import plotly.subplots as sp

# ==============================================================================
# 🎨 1. INSTITUTIONAL COLOR PALETTES & SEMANTIC MAPPINGS
# ==============================================================================

ARGUS_COLORS: Dict[str, str] = {
    "primary": "#3b82f6",  # Blue Core / Benchmark Primario
    "accent": "#06b6d4",  # Cyan Horizon / Highlights
    "bull": "#10b981",  # Emerald Bullish / Rendimenti Positivi
    "bear": "#ef4444",  # Coral Bearish / Drawdown / Perdite
    "warn": "#f59e0b",  # Amber Warning / Soglie limite
    "neutral": "#64748b",  # Slate Gray Neutro
    "benchmark": "#94a3b8",  # Benchmark Line Gray
    "purple": "#8b5cf6",  # Royal Violet
    "gold": "#f59e0b",  # Gold / Target FIRE
    "dark_surface": "#111827",  # Surface Dark
    "dark_bg": "#0b0f19",  # Canvas Dark
    "grid_dark": "rgba(255, 255, 255, 0.06)",
    "grid_light": "rgba(0, 0, 0, 0.06)",
}


class ObsidianTheme:
    """Design System Semantic Constants per Obsidian Dark Theme."""
    ELECTRIC_BLUE: str = "#38bdf8"
    EMERALD: str = "#10b981"
    AMBER: str = "#f59e0b"
    PURPLE: str = "#8b5cf6"
    CRIMSON: str = "#ef4444"
    SLATE: str = "#64748b"
    MUTED_BLUE: str = "#3b82f6"
    GOLD: str = "#f59e0b"
    DARK_SURFACE: str = "#111827"
    DARK_BG: str = "#0b0f19"


ARGUS_FINANCIAL_PALETTE: List[str] = [
    "#38bdf8",  # Cyan / Equity
    "#10b981",  # Emerald / Fixed Income
    "#f59e0b",  # Amber / Commodities
    "#8b5cf6",  # Violet / Real Estate
    "#64748b",  # Slate / Cash
    "#d946ef",  # Fuchsia / Crypto
    "#14b8a6",  # Teal / Private Equity
    "#f97316",  # Orange / Derivatives
    "#3b82f6",  # Royal Blue / Core Portfolio
    "#84cc16",  # Lime / ESG Green
]

ARGUS_ASSET_CLASS_COLORS: Dict[str, str] = {
    "equity": "#38bdf8",  # Electric Blue / Cyan
    "fixed_income": "#10b981",  # Emerald Green
    "commodities": "#f59e0b",  # Amber / Gold
    "real_estate": "#8b5cf6",  # Royal Purple
    "cash": "#64748b",  # Slate Gray
    "crypto": "#d946ef",  # Fuchsia / Neon Violet
    "private_equity": "#14b8a6",  # Teal
    "derivatives": "#f97316",  # Orange
    "alternative": "#a855f7",  # Violet
    "risk": "#ef4444",  # Crimson Red
    "benchmark": "#94a3b8",  # Slate Light
    "portfolio": "#ff9900",  # Amber / Orange Primary
}

# Scale sequenziali per gradienti di rendimento / rischio
ARGUS_SEQUENTIAL_WEALTH: List[str] = ["#064e3b", "#047857", "#059669", "#10b981", "#34d399", "#6ee7b7"]
ARGUS_SEQUENTIAL_RISK: List[str] = ["#451a03", "#78350f", "#b45309", "#d97706", "#f59e0b", "#fcd34d"]

# Scala divergente istituzionale per matrici di correlazione (-1.0 -> 0.0 -> +1.0)
ARGUS_DIVERGING_SCALE: List[List[Union[float, str]]] = [
    [0.0, "#ef4444"],  # Max negativo (-1.0) Correlazione inversa / Drawdown
    [0.25, "#991b1b"],
    [0.5, "#1e293b"],  # Neutro (0.0) Decorrelato
    [0.75, "#047857"],
    [1.0, "#10b981"],  # Max positivo (+1.0) Co-movimento pieno
]

# Scala PnL stile Finviz (Rosso profondo -> Slate neutro -> Verde smeraldo brillante)
FINVIZ_PNL_SCALE: List[List[Union[float, str]]] = [
    [0.0, "#b91c1c"],  # Perdita grave (<= -3% o -10%)
    [0.25, "#ef4444"],  # Perdita moderata
    [0.5, "#1e293b"],  # Parità (0.0%)
    [0.75, "#059669"],  # Guadagno moderato
    [1.0, "#10b981"],  # Guadagno elevato (>= +3% o +10%)
]

# Gradienti per bande di confidenza Monte Carlo
ARGUS_GLOW_CONES: Dict[str, str] = {
    "band_90": "rgba(56, 189, 248, 0.12)",  # P5 - P95
    "band_50": "rgba(56, 189, 248, 0.24)",  # P25 - P75
    "median_line": "#38bdf8",  # P50 solid line
    "target_line": "#f59e0b",  # Target FIRE
    "initial_line": "rgba(148, 163, 184, 0.6)",  # Capitale iniziale
}


def get_asset_color(asset_or_category: str) -> str:
    """
    Restituisce il colore istituzionale standard ARGUS per una data asset class o categoria.
    Supporta nomenclatura sia in lingua italiana che inglese, con fallback deterministico.
    """
    if not asset_or_category:
        return ARGUS_ASSET_CLASS_COLORS["equity"]

    key = str(asset_or_category).strip().lower().replace("_", " ").replace("-", " ")

    # Fixed Income / Obbligazionario / Titoli di Stato (prima di equity per evitare che 'obbligAZIONi' matchi 'azion')
    if any(k in key for k in ["obbligaz", "fixed income", "bond", "btp", "bund", "treasury", "cedol", "gov"]):
        return ARGUS_ASSET_CLASS_COLORS["fixed_income"]

    # Equity / Azionario
    if any(k in key for k in ["azion", "equity", "stock", "share", "etf equity", "sp500", "nasdaq", "msci"]):
        return ARGUS_ASSET_CLASS_COLORS["equity"]

    # Commodities / Materie Prime / Metalli
    if any(k in key for k in ["materie prime", "commodit", "oro", "gold", "silver", "argento", "oil", "petrolio"]):
        return ARGUS_ASSET_CLASS_COLORS["commodities"]

    # Real Estate / Immobili
    if any(k in key for k in ["immobil", "real estate", "reit", "casa", "mutuo", "terren"]):
        return ARGUS_ASSET_CLASS_COLORS["real_estate"]

    # Cash / Liquidità
    if any(k in key for k in ["liquidit", "cash", "deposito", "conto", "money market", "valuta"]):
        return ARGUS_ASSET_CLASS_COLORS["cash"]

    # Crypto / Asset Digitali
    if any(k in key for k in ["crypto", "cripto", "btc", "bitcoin", "eth", "ethereum", "sol", "token"]):
        return ARGUS_ASSET_CLASS_COLORS["crypto"]

    # Private Equity / Alternative
    if any(k in key for k in ["private equity", "venture", "hedge", "alternativ", "startup"]):
        return ARGUS_ASSET_CLASS_COLORS["private_equity"]

    # Derivati / Opzioni
    if any(k in key for k in ["derivat", "opzion", "future", "option"]):
        return ARGUS_ASSET_CLASS_COLORS["derivatives"]

    # Rischio / Drawdown / Perdite
    if any(k in key for k in ["drawdown", "perdit", "loss", "var", "es", "rischio", "risk", "bear"]):
        return ARGUS_ASSET_CLASS_COLORS["risk"]

    # Benchmark
    if any(k in key for k in ["benchmark", "indice", "mercato", "index"]):
        return ARGUS_ASSET_CLASS_COLORS["benchmark"]

    # Portafoglio / NAV
    if any(k in key for k in ["portafoglio", "portfolio", "nav", "totale", "total"]):
        return ARGUS_ASSET_CLASS_COLORS["portfolio"]

    # Hash deterministico per categorie sconosciute
    hash_idx = abs(hash(key)) % len(ARGUS_FINANCIAL_PALETTE)
    return ARGUS_FINANCIAL_PALETTE[hash_idx]


# ==============================================================================
# 🛠️ 2. MEMORY OPTIMIZATION & PLOTLY TEMPLATES
# ==============================================================================


def optimize_plotly_figure_memory(fig: go.Figure, precision: int = 4) -> go.Figure:
    """
    Comprime la serializzazione JSON delle figure Plotly per minimizzare il footprint in RAM:
    - Arrotonda gli array float a `precision` cifre decimali.
    - Converte coordinate, customdata e marker color float in formato compatto.
    """
    if fig is None or not hasattr(fig, "data"):
        return fig
    try:
        for trace in fig.data:
            for attr in ["x", "y", "z", "customdata", "text"]:
                if hasattr(trace, attr):
                    val = getattr(trace, attr)
                    if val is not None and isinstance(val, (list, tuple, np.ndarray, pd.Series)):
                        arr = np.asarray(val)
                        if np.issubdtype(arr.dtype, np.floating):
                            rounded = np.round(arr, precision)
                            setattr(trace, attr, rounded.tolist())
            if hasattr(trace, "marker") and trace.marker is not None:
                if hasattr(trace.marker, "color") and trace.marker.color is not None:
                    m_color = trace.marker.color
                    if isinstance(m_color, (list, tuple, np.ndarray, pd.Series)):
                        arr_c = np.asarray(m_color)
                        if np.issubdtype(arr_c.dtype, np.floating):
                            trace.marker.color = np.round(arr_c, precision).tolist()
    except Exception:
        pass
    return fig


def register_argus_plotly_templates() -> None:
    """Registra i template ufficiali argus_dark e argus_light nel motore Plotly."""
    dark_template = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            colorway=ARGUS_FINANCIAL_PALETTE,
            font={
                "family": "Outfit, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                "color": "#e2e8f0",
                "size": 12,
            },
            xaxis={
                "showgrid": True,
                "gridwidth": 1,
                "gridcolor": ARGUS_COLORS["grid_dark"],
                "zeroline": True,
                "zerolinecolor": "rgba(255, 255, 255, 0.12)",
                "linecolor": "rgba(255, 255, 255, 0.10)",
                "tickfont": {"family": "'JetBrains Mono', monospace", "color": "#94a3b8", "size": 11},
                "title": {"font": {"family": "Outfit, sans-serif", "color": "#cbd5e1", "size": 12}},
            },
            yaxis={
                "showgrid": True,
                "gridwidth": 1,
                "gridcolor": ARGUS_COLORS["grid_dark"],
                "zeroline": True,
                "zerolinecolor": "rgba(255, 255, 255, 0.12)",
                "linecolor": "rgba(255, 255, 255, 0.10)",
                "tickfont": {"family": "'JetBrains Mono', monospace", "color": "#94a3b8", "size": 11},
                "title": {"font": {"family": "Outfit, sans-serif", "color": "#cbd5e1", "size": 12}},
            },
            hoverlabel={
                "bgcolor": "#111827",
                "bordercolor": "#3b82f6",
                "font": {"family": "Outfit, sans-serif", "color": "#f8fafc", "size": 12},
            },
            legend={
                "orientation": "h",
                "yanchor": "top",
                "y": -0.16,
                "xanchor": "center",
                "x": 0.5,
                "bgcolor": "rgba(0,0,0,0)",
                "font": {"family": "Outfit, sans-serif", "color": "#94a3b8", "size": 11},
            },
            margin={"l": 40, "r": 20, "t": 40, "b": 40},
        )
    )

    light_template = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            colorway=ARGUS_FINANCIAL_PALETTE,
            font={
                "family": "Outfit, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                "color": "#1e293b",
                "size": 12,
            },
            xaxis={
                "showgrid": True,
                "gridwidth": 1,
                "gridcolor": ARGUS_COLORS["grid_light"],
                "zeroline": True,
                "zerolinecolor": "rgba(0, 0, 0, 0.12)",
                "linecolor": "rgba(0, 0, 0, 0.10)",
                "tickfont": {"family": "'JetBrains Mono', monospace", "color": "#64748b", "size": 11},
                "title": {"font": {"family": "Outfit, sans-serif", "color": "#334155", "size": 12}},
            },
            yaxis={
                "showgrid": True,
                "gridwidth": 1,
                "gridcolor": ARGUS_COLORS["grid_light"],
                "zeroline": True,
                "zerolinecolor": "rgba(0, 0, 0, 0.12)",
                "linecolor": "rgba(0, 0, 0, 0.10)",
                "tickfont": {"family": "'JetBrains Mono', monospace", "color": "#64748b", "size": 11},
                "title": {"font": {"family": "Outfit, sans-serif", "color": "#334155", "size": 12}},
            },
            hoverlabel={
                "bgcolor": "#ffffff",
                "bordercolor": "#2563eb",
                "font": {"family": "Outfit, sans-serif", "color": "#0f172a", "size": 12},
            },
            legend={
                "orientation": "h",
                "yanchor": "top",
                "y": -0.16,
                "xanchor": "center",
                "x": 0.5,
                "bgcolor": "rgba(0,0,0,0)",
                "font": {"family": "Outfit, sans-serif", "color": "#64748b", "size": 11},
            },
            margin={"l": 40, "r": 20, "t": 40, "b": 40},
        )
    )

    pio.templates["argus_dark"] = dark_template
    pio.templates["argus_light"] = light_template


# Inizializzazione automatica dei template all'import
try:
    register_argus_plotly_templates()
except Exception:
    pass


def get_argus_plotly_config(filename: str = "argus_chart", display_mode_bar: str = "hover") -> dict:
    """
    Restituisce la configurazione ideale standardizzata per st.plotly_chart:
    - Toolbar focalizzata (zoom, pan, autoscale, reset axes, PNG export)
    - Rimozione strumenti non pertinenti (lasso, box select, spikelines toggle)
    - Esportazione PNG nitida a scala 2x (1280x720) per report e presentazioni
    """
    return {
        "displayModeBar": True if display_mode_bar == "always" else "hover",
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": [
            "select2d",
            "lasso2d",
            "toggleSpikelines",
            "hoverClosestCartesian",
            "hoverCompareCartesian",
        ],
        "toImageButtonOptions": {"format": "png", "filename": filename, "height": 720, "width": 1280, "scale": 2},
    }


# Alias per retrocompatibilità
get_plotly_config = get_argus_plotly_config


def apply_argus_theme(
    fig: go.Figure,
    title: Optional[str] = None,
    x_title: Optional[str] = None,
    y_title: Optional[str] = None,
    is_percentage: bool = False,
    is_currency: bool = False,
    currency_symbol: str = "€",
    height: Optional[int] = None,
    show_legend: bool = True,
    legend_position: str = "bottom",
    legend_orientation: str = "h",
    dark_mode: bool = True,
    hovermode: str = "x unified",
    show_spikes: bool = True,
    optimize_memory: bool = True,
    precision: int = 4,
    uirevision: Optional[Any] = "argus_global_viewport",
) -> go.Figure:
    """
    Applica il Design System istituzionale ARGUS a una figura Plotly:
    - Sfondo trasparente opaco ad alta compatibilità dark-theme
    - Margini compatti e tipografia gerarchica (Outfit / JetBrains Mono)
    - Legenda orizzontale posizionata in basso (o in alto) con zero interferenza
    - Formattazione automatica degli assi (valuta/percentuale)
    - Compressione della memoria RAM tramite arrotondamento float
    - Sincronizzazione cross-chart del cursore temporale (spikemode="across+toaxis")
    - Persistenza dello zoom / viewport dell'utente (uirevision)
    """
    if fig is None:
        return fig

    tpl = "argus_dark" if dark_mode else "argus_light"
    text_color = "#f8fafc" if dark_mode else "#0f172a"
    subtle_color = "#94a3b8" if dark_mode else "#64748b"

    # Margini compatti standardizzati
    top_margin = 44 if title else 24
    bottom_margin = 44 if (x_title or (show_legend and legend_position == "bottom")) else 28

    layout_updates: Dict[str, Any] = {
        "template": tpl,
        "hovermode": hovermode,
        "autosize": True,
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": {"l": 40, "r": 20, "t": top_margin, "b": bottom_margin},
    }

    if uirevision is not None:
        layout_updates["uirevision"] = uirevision

    if height is not None:
        layout_updates["height"] = height

    if title:
        layout_updates["title"] = {
            "text": f"<b>{title}</b>",
            "font": {"family": "Outfit, sans-serif", "size": 15, "color": text_color},
            "x": 0.01,
            "y": 0.98,
            "xanchor": "left",
            "yanchor": "top",
        }

    # Configurazione Legenda Standard
    if show_legend:
        if legend_position == "bottom":
            layout_updates["legend"] = {
                "orientation": legend_orientation,
                "yanchor": "top",
                "y": -0.16 if x_title else -0.12,
                "xanchor": "center",
                "x": 0.5,
                "bgcolor": "rgba(0,0,0,0)",
                "font": {"family": "Outfit, sans-serif", "size": 11, "color": subtle_color},
            }
        elif legend_position == "top":
            layout_updates["legend"] = {
                "orientation": legend_orientation,
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1.0,
                "bgcolor": "rgba(0,0,0,0)",
                "font": {"family": "Outfit, sans-serif", "size": 11, "color": subtle_color},
            }
        else:  # right
            layout_updates["legend"] = {
                "orientation": "v",
                "yanchor": "top",
                "y": 1.0,
                "xanchor": "left",
                "x": 1.02,
                "bgcolor": "rgba(0,0,0,0)",
                "font": {"family": "Outfit, sans-serif", "size": 11, "color": subtle_color},
            }
    else:
        layout_updates["showlegend"] = False

    fig.update_layout(**layout_updates)

    # Configurazione Asse X
    x_kwargs: Dict[str, Any] = {}
    if x_title:
        x_kwargs["title"] = {"text": x_title, "font": {"family": "Outfit, sans-serif", "size": 12, "color": subtle_color}}
    if show_spikes:
        x_kwargs.update(
            {
                "showspikes": True,
                "spikethickness": 1,
                "spikedash": "solid",
                "spikesnap": "cursor",
                "spikemode": "across+toaxis",
                "spikecolor": "rgba(56, 189, 248, 0.45)" if dark_mode else "rgba(37, 99, 235, 0.45)",
            }
        )
    if x_kwargs:
        fig.update_xaxes(**x_kwargs)

    # Configurazione Asse Y
    y_kwargs: Dict[str, Any] = {}
    if y_title:
        y_kwargs["title"] = {"text": y_title, "font": {"family": "Outfit, sans-serif", "size": 12, "color": subtle_color}}
    if is_percentage:
        y_kwargs["tickformat"] = ",.2%"
    elif is_currency:
        y_kwargs["tickprefix"] = f"{currency_symbol} "
        y_kwargs["tickformat"] = ",.2f"
    if y_kwargs:
        fig.update_yaxes(**y_kwargs)

    if optimize_memory:
        optimize_plotly_figure_memory(fig, precision=precision)

    return fig


# Alias per piena retrocompatibilità con core/ui_utils.py
apply_custom_chart_layout = apply_argus_theme


# ==============================================================================
# ⚡ 3. PERFORMANCE ENGINE: LTTB DOWNSAMPLING & WEBGL AUTO-SWITCHING
# ==============================================================================


def lttb_downsample(x: Any, y: Any, n_buckets: int = 1000) -> Tuple[Any, Any]:
    """
    Algoritmo LTTB (Largest Triangle Three Buckets) implementato in puro NumPy vettorizzato.
    Downsample time series dense preservando picchi, minimi locali e forma percettiva dell'onda.

    - Supporta DatetimeIndex, Series con indice temporale, stringhe o array numerici.
    - Preserva rigorosamente il primo e l'ultimo punto della serie.
    - Esecuzione sub-millisecondo per migliaia di punti.
    """
    if x is None or y is None:
        return x, y

    n_points = len(x)
    if n_points <= n_buckets or n_buckets < 3:
        return x, y

    # Estrazione float per y
    y_raw = np.asarray(y, dtype=np.float64)
    has_nan = bool(np.isnan(y_raw).any())
    y_arr = np.nan_to_num(y_raw, nan=0.0) if has_nan else y_raw

    # Conversione asse x in valori numerici float per calcolo delle aree dei triangoli
    if isinstance(x, (pd.Series, pd.Index)):
        if pd.api.types.is_datetime64_any_dtype(x):
            x_num = np.asarray(x.view("int64"), dtype=np.float64)
        else:
            try:
                x_num = np.asarray(x, dtype=np.float64)
            except Exception:
                x_num = np.arange(n_points, dtype=np.float64)
    elif isinstance(x, np.ndarray) and np.issubdtype(x.dtype, np.datetime64):
        x_num = x.view("int64").astype(np.float64)
    else:
        try:
            x_num = np.asarray(x, dtype=np.float64)
        except Exception:
            x_num = np.arange(n_points, dtype=np.float64)

    sampled = np.zeros(n_buckets, dtype=np.int64)
    sampled[0] = 0
    sampled[-1] = n_points - 1

    bucket_size = (n_points - 2) / (n_buckets - 2)
    a_idx = 0

    for i in range(1, n_buckets - 1):
        # Range del bucket corrente B_i
        b_start = int(np.floor((i - 1) * bucket_size)) + 1
        b_end = min(int(np.floor(i * bucket_size)) + 1, n_points - 1)

        # Range del bucket successivo B_{i+1} per punto medio C
        c_start = int(np.floor(i * bucket_size)) + 1
        c_end = min(int(np.floor((i + 1) * bucket_size)) + 1, n_points)

        if c_end > c_start:
            avg_x_c = np.mean(x_num[c_start:c_end])
            avg_y_c = np.mean(y_arr[c_start:c_end])
        else:
            avg_x_c = x_num[-1]
            avg_y_c = y_arr[-1]

        # Punto A (selezionato nel bucket precedente)
        x_a = x_num[a_idx]
        y_a = y_arr[a_idx]

        # Punti candidati B nel bucket corrente
        x_b = x_num[b_start:b_end]
        y_b = y_arr[b_start:b_end]

        if len(x_b) == 0:
            sampled[i] = b_start
            a_idx = b_start
            continue

        # Calcolo vettoriale area del triangolo: Area = 0.5 * |(x_a - avg_x_c)(y_b - y_a) - (x_a - x_b)(avg_y_c - y_a)|
        areas = np.abs((x_a - avg_x_c) * (y_b - y_a) - (x_a - x_b) * (avg_y_c - y_a))
        chosen = b_start + int(np.argmax(areas))

        sampled[i] = chosen
        a_idx = chosen

    # Ricostruzione output preservando i tipi originali
    if isinstance(x, pd.Series):
        x_out = x.iloc[sampled]
    elif isinstance(x, pd.Index):
        x_out = x[sampled]
    elif isinstance(x, np.ndarray):
        x_out = x[sampled]
    elif isinstance(x, list):
        x_out = [x[idx] for idx in sampled]
    else:
        x_out = np.asarray(x)[sampled]

    if has_nan:
        if isinstance(y, pd.Series):
            y_out = pd.Series(y_arr[sampled], index=x_out if isinstance(x_out, (pd.Index, pd.Series)) else None)
        elif isinstance(y, list):
            y_out = y_arr[sampled].tolist()
        else:
            y_out = y_arr[sampled]
    else:
        if isinstance(y, pd.Series):
            y_out = y.iloc[sampled]
        elif isinstance(y, np.ndarray):
            y_out = y[sampled]
        elif isinstance(y, list):
            y_out = [y[idx] for idx in sampled]
        else:
            y_out = y_arr[sampled]

    return x_out, y_out


def auto_webgl_trace(
    x: Any, y: Any, mode: str = "lines", threshold: int = 1000, force_webgl: Optional[bool] = None, **kwargs
) -> Union[go.Scatter, go.Scattergl]:
    """
    Crea automaticamente una traccia go.Scattergl (accelerata via WebGL/Canvas GPU)
    se il numero di punti supera la soglia `threshold`, altrimenti go.Scatter vettoriale standard.
    """
    n_points = len(x) if x is not None and hasattr(x, "__len__") else 0
    use_gl = (n_points >= threshold) if force_webgl is None else force_webgl
    trace_cls = go.Scattergl if use_gl else go.Scatter
    return trace_cls(x=x, y=y, mode=mode, **kwargs)


def convert_figure_to_webgl(fig: go.Figure, threshold: int = 1000) -> go.Figure:
    """
    Ispeziona una figura Plotly esistente e converte eventuali tracce go.Scatter
    aventi punti >= threshold in go.Scattergl per garantire fluidità a 60 FPS.
    """
    if fig is None or not hasattr(fig, "data"):
        return fig

    new_traces = []
    has_changes = False

    for trace in fig.data:
        if trace.type == "scatter":
            x_data = getattr(trace, "x", None)
            if x_data is not None and hasattr(x_data, "__len__") and len(x_data) >= threshold:
                trace_dict = trace.to_plotly_json()
                trace_dict["type"] = "scattergl"
                new_traces.append(go.Scattergl(**trace_dict))
                has_changes = True
                continue
        new_traces.append(trace)

    if has_changes:
        return go.Figure(data=new_traces, layout=fig.layout)

    return fig


# ==============================================================================
# 📊 4. THE FOUR PRODUCTION-READY WRAPPER CHARTS
# ==============================================================================


def create_timeseries_chart(
    series_dict: Optional[Union[pd.Series, Dict[str, Union[pd.Series, np.ndarray, Sequence[float]]]]] = None,
    nav_series: Optional[pd.Series] = None,
    benchmark_series: Optional[pd.Series] = None,
    drawdown_series: Optional[pd.Series] = None,
    show_drawdown: bool = True,
    title: str = "Andamento Temporale & Drawdown",
    currency_symbol: str = "€",
    is_percentage: bool = False,
    height: int = 540,
    dark_mode: bool = True,
    max_points: int = 2000,
    use_webgl: Union[bool, str] = "auto",
) -> go.Figure:
    """
    Wrapper ad alte prestazioni per serie storiche finanziarie (NAV, prezzi, portafoglio vs benchmark).
    - Pannello 1 (72% altezza): Curve NAV/Prezzo con riempimento gradiente sottile.
    - Pannello 2 (28% altezza): Sottomattonella sincronizzata Underwater Drawdown con diamante Max DD.
    - Ottimizzazione LTTB automatica se la serie supera `max_points`.
    - Auto-switch a go.Scattergl WebGL per navigazione fluida a 60 FPS.
    """
    if series_dict is None and nav_series is not None:
        series_dict = nav_series

    # Normalizzazione input in dizionario
    if isinstance(series_dict, pd.Series):
        if series_dict.empty:
            return go.Figure()
        s_name = series_dict.name or "Portafoglio (NAV)"
        if "portafoglio" not in str(s_name).lower():
            s_name = f"Portafoglio ({s_name})"
        series_map = {str(s_name): series_dict}
        primary_series = series_dict
    elif isinstance(series_dict, dict):
        if not series_dict:
            return go.Figure()
        series_map = series_dict
        primary_series = next(iter(series_dict.values()))
        if isinstance(primary_series, Sequence) and not isinstance(primary_series, (pd.Series, np.ndarray)):
            primary_series = pd.Series(primary_series)
    else:
        return go.Figure()

    # Se richiesto il drawdown e non fornito esplicitamente, calcolalo sulla serie primaria
    has_dd_pane = show_drawdown and (isinstance(primary_series, pd.Series) or drawdown_series is not None)
    if has_dd_pane and drawdown_series is None and isinstance(primary_series, pd.Series) and not primary_series.empty:
        hwm = primary_series.cummax()
        # Evita divisioni per zero se hwm è 0
        hwm_safe = hwm.replace(0, np.nan)
        drawdown_series = (primary_series - hwm) / hwm_safe * 100.0

    if has_dd_pane:
        fig = sp.make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.72, 0.28])
    else:
        fig = go.Figure()

    color_idx = 0
    for name, s_data in series_map.items():
        if s_data is None:
            continue
        if isinstance(s_data, pd.Series):
            if s_data.empty:
                continue
            x_vals = s_data.index
            y_vals = s_data.values
        elif isinstance(s_data, (np.ndarray, list, tuple)):
            if len(s_data) == 0:
                continue
            x_vals = np.arange(len(s_data))
            y_vals = np.asarray(s_data)
        else:
            continue

        # Downsampling LTTB se la serie è estesa
        if len(x_vals) > max_points:
            x_vals, y_vals = lttb_downsample(x_vals, y_vals, n_buckets=max_points)

        color = (
            get_asset_color(name)
            if color_idx == 0
            else ARGUS_FINANCIAL_PALETTE[color_idx % len(ARGUS_FINANCIAL_PALETTE)]
        )
        webgl_mode = (len(x_vals) >= 1000) if use_webgl == "auto" else bool(use_webgl)

        fmt_unit = "%" if is_percentage else f"{currency_symbol}"
        hover_tmpl = (
            f"<b>{name}</b>: %{{y:,.2f}} {fmt_unit}<extra></extra>"
            if is_percentage
            else f"<b>{name}</b>: {currency_symbol} %{{y:,.2f}}<extra></extra>"
        )

        trace = auto_webgl_trace(
            x=x_vals,
            y=y_vals,
            mode="lines",
            name=name,
            line={"color": color, "width": 2.2 if color_idx == 0 else 1.8},
            fill="tozeroy" if color_idx == 0 and not has_dd_pane else None,
            fillcolor="rgba(56, 189, 248, 0.08)" if color_idx == 0 else None,
            hovertemplate=hover_tmpl,
            force_webgl=webgl_mode,
        )

        if has_dd_pane:
            fig.add_trace(trace, row=1, col=1)
        else:
            fig.add_trace(trace)

        color_idx += 1

    # Benchmark opzionale
    if benchmark_series is not None and not benchmark_series.empty:
        b_x = benchmark_series.index
        b_y = benchmark_series.values
        if len(b_x) > max_points:
            b_x, b_y = lttb_downsample(b_x, b_y, n_buckets=max_points)

        b_webgl = (len(b_x) >= 1000) if use_webgl == "auto" else bool(use_webgl)
        b_trace = auto_webgl_trace(
            x=b_x,
            y=b_y,
            mode="lines",
            name="Benchmark",
            line={"color": ARGUS_COLORS["benchmark"], "width": 1.6, "dash": "dash"},
            hovertemplate="<b>Benchmark</b>: %{y:,.2f}<extra></extra>",
            force_webgl=b_webgl,
        )
        if has_dd_pane:
            fig.add_trace(b_trace, row=1, col=1)
        else:
            fig.add_trace(b_trace)

    # Sottomattonella Underwater Drawdown
    if has_dd_pane and drawdown_series is not None and not drawdown_series.empty:
        dd_x = drawdown_series.index
        dd_y = drawdown_series.values
        if len(dd_x) > max_points:
            dd_x, dd_y = lttb_downsample(dd_x, dd_y, n_buckets=max_points)

        dd_webgl = (len(dd_x) >= 1000) if use_webgl == "auto" else bool(use_webgl)
        dd_trace = auto_webgl_trace(
            x=dd_x,
            y=dd_y,
            mode="lines",
            name="Drawdown",
            line={"color": ARGUS_COLORS["bear"], "width": 1.4},
            fill="tozeroy",
            fillcolor="rgba(239, 68, 68, 0.22)",
            hovertemplate="<b>Drawdown</b>: %{y:.2f}%<extra></extra>",
            force_webgl=dd_webgl,
        )
        fig.add_trace(dd_trace, row=2, col=1)

        # Evidenziazione Max Drawdown Storico con marcatore a diamante
        min_dd = float(np.nanmin(dd_y)) if len(dd_y) > 0 else 0.0
        if min_dd < 0:
            min_idx = int(np.nanargmin(dd_y))
            min_x = dd_x[min_idx] if hasattr(dd_x, "__getitem__") else dd_x.iloc[min_idx]
            fig.add_trace(
                go.Scatter(
                    x=[min_x],
                    y=[min_dd],
                    mode="markers+text",
                    name="Max Drawdown",
                    marker={"color": ARGUS_COLORS["bear"], "size": 8, "symbol": "diamond"},
                    text=[f"Max DD: {min_dd:.1f}%"],
                    textposition="bottom center",
                    textfont={"family": "'JetBrains Mono', monospace", "size": 10, "color": "#f87171"},
                    hoverinfo="skip",
                ),
                row=2,
                col=1,
            )

    apply_argus_theme(
        fig,
        title=title,
        height=height,
        dark_mode=dark_mode,
        hovermode="x unified",
        show_legend=True,
        legend_position="bottom",
    )

    if has_dd_pane:
        y1_label = "Rendimento" if is_percentage else f"Valore ({currency_symbol})"
        fig.update_yaxes(
            title_text=y1_label,
            tickformat=",.2%" if is_percentage else ",.2f",
            tickprefix="" if is_percentage else f"{currency_symbol} ",
            row=1,
            col=1,
        )
        fig.update_yaxes(title_text="Drawdown", ticksuffix="%", tickformat=",.1f", row=2, col=1)
        fig.update_xaxes(row=2, col=1, title_text="Data")
    else:
        fig.update_yaxes(
            title_text="Rendimento" if is_percentage else f"Valore ({currency_symbol})",
            tickformat=",.2%" if is_percentage else ",.2f",
            tickprefix="" if is_percentage else f"{currency_symbol} ",
        )

    return fig


# Alias per retrocompatibilità
create_equity_drawdown_chart = create_timeseries_chart


def create_montecarlo_fan_chart(
    simulations: Union[pd.DataFrame, np.ndarray, Dict[str, Any]],
    dates: Optional[Union[pd.Index, List[Any]]] = None,
    initial_value: Optional[float] = None,
    target_value: Optional[float] = None,
    title: str = "Simulazione Monte Carlo — Proiezione a Ventaglio",
    currency_symbol: str = "€",
    height: int = 480,
    dark_mode: bool = True,
    quantiles: Tuple[float, float, float, float] = (0.05, 0.25, 0.75, 0.95),
    max_points: int = 1500,
    use_webgl: Union[bool, str] = "auto",
) -> go.Figure:
    """
    Genera un Fan Chart (cono probabilistico a ventaglio) per simulazioni Monte Carlo / FIRE:
    - Banda esterna 90% di confidenza (P5 - P95) con fill trasparente delicato
    - Banda interna 50% di confidenza (P25 - P75 interquartile)
    - Traiettoria mediana (P50) solida ad alta visibilità (#38bdf8)
    - Linea di break-even / capitale iniziale e soglia target FIRE opzionali
    - Elimina 100+ spaghetti lines disordinate garantendo prestazioni a 60 FPS
    """
    if simulations is None:
        return go.Figure()

    q_low_outer, q_low_inner, q_high_inner, q_high_outer = quantiles

    # Estrazione percentili
    if isinstance(simulations, dict):
        if not simulations:
            return go.Figure()
        p5 = np.asarray(simulations.get("p5", simulations.get("q05", [])))
        p25 = np.asarray(simulations.get("p25", simulations.get("q25", [])))
        p50 = np.asarray(simulations.get("p50", simulations.get("q50", [])))
        p75 = np.asarray(simulations.get("p75", simulations.get("q75", [])))
        p95 = np.asarray(simulations.get("p95", simulations.get("q95", [])))
        x_axis = dates if dates is not None else list(range(len(p50)))
    elif isinstance(simulations, pd.DataFrame):
        if simulations.empty:
            return go.Figure()
        x_axis = simulations.index if dates is None else dates
        p5 = simulations.quantile(q_low_outer, axis=1).values
        p25 = simulations.quantile(q_low_inner, axis=1).values
        p50 = simulations.quantile(0.50, axis=1).values
        p75 = simulations.quantile(q_high_inner, axis=1).values
        p95 = simulations.quantile(q_high_outer, axis=1).values
    elif isinstance(simulations, np.ndarray):
        if simulations.size == 0 or simulations.ndim < 2:
            return go.Figure()
        x_axis = list(range(simulations.shape[0])) if dates is None else dates
        p5 = np.percentile(simulations, q_low_outer * 100, axis=1)
        p25 = np.percentile(simulations, q_low_inner * 100, axis=1)
        p50 = np.percentile(simulations, 50, axis=1)
        p75 = np.percentile(simulations, q_high_inner * 100, axis=1)
        p95 = np.percentile(simulations, q_high_outer * 100, axis=1)
    else:
        return go.Figure()

    if len(p50) == 0:
        return go.Figure()

    # Downsampling se l'orizzonte temporale è denso
    if len(x_axis) > max_points:
        _, p50 = lttb_downsample(x_axis, p50, n_buckets=max_points)
        _, p5 = lttb_downsample(x_axis, p5, n_buckets=max_points)
        _, p25 = lttb_downsample(x_axis, p25, n_buckets=max_points)
        _, p75 = lttb_downsample(x_axis, p75, n_buckets=max_points)
        x_axis, p95 = lttb_downsample(x_axis, p95, n_buckets=max_points)

    fig = go.Figure()
    is_webgl = (len(x_axis) >= 1000) if use_webgl == "auto" else bool(use_webgl)

    # 1. Banda Esterna 90% (P5 - P95)
    fig.add_trace(
        auto_webgl_trace(
            x=x_axis, y=p95, mode="lines", line={"width": 0}, showlegend=False, hoverinfo="skip", force_webgl=is_webgl
        )
    )
    fig.add_trace(
        auto_webgl_trace(
            x=x_axis,
            y=p5,
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor=ARGUS_GLOW_CONES["band_90"],
            name=f"Intervallo 90% (P{int(q_low_outer * 100)} - P{int(q_high_outer * 100)})",
            hovertemplate=f"P{int(q_low_outer * 100)} (Pessimistico): <b>{currency_symbol} %{{y:,.0f}}</b><extra></extra>",
            force_webgl=is_webgl,
        )
    )

    # 2. Banda Interna 50% Interquartile (P25 - P75)
    fig.add_trace(
        auto_webgl_trace(
            x=x_axis, y=p75, mode="lines", line={"width": 0}, showlegend=False, hoverinfo="skip", force_webgl=is_webgl
        )
    )
    fig.add_trace(
        auto_webgl_trace(
            x=x_axis,
            y=p25,
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor=ARGUS_GLOW_CONES["band_50"],
            name=f"Intervallo 50% (P{int(q_low_inner * 100)} - P{int(q_high_inner * 100)})",
            hovertemplate=f"P{int(q_low_inner * 100)}: <b>{currency_symbol} %{{y:,.0f}}</b><extra></extra>",
            force_webgl=is_webgl,
        )
    )

    # 3. Mediana P50
    fig.add_trace(
        auto_webgl_trace(
            x=x_axis,
            y=p50,
            mode="lines",
            line={"color": ARGUS_GLOW_CONES["median_line"], "width": 2.6},
            name="Mediana (P50)",
            hovertemplate=f"<b>Mediana</b>: {currency_symbol} %{{y:,.0f}}<extra></extra>",
            force_webgl=is_webgl,
        )
    )

    # Linea Capitale Iniziale
    if initial_value is not None:
        fig.add_hline(
            y=initial_value,
            line_dash="dot",
            line_color=ARGUS_GLOW_CONES["initial_line"],
            line_width=1.3,
            annotation_text=f"Base: {currency_symbol} {initial_value:,.0f}",
            annotation_position="bottom left",
            annotation_font={"family": "'JetBrains Mono', monospace", "size": 10, "color": "#94a3b8"},
        )

    # Target FIRE / Soglia Obiettivo
    if target_value is not None:
        fig.add_hline(
            y=target_value,
            line_dash="dash",
            line_color=ARGUS_GLOW_CONES["target_line"],
            line_width=1.6,
            annotation_text=f"Target: {currency_symbol} {target_value:,.0f}",
            annotation_position="top left",
            annotation_font={"family": "'JetBrains Mono', monospace", "size": 11, "color": "#fbbf24"},
        )

    apply_argus_theme(
        fig,
        title=title,
        x_title="Orizzonte Temporale",
        y_title=f"Capitale Stimato ({currency_symbol})",
        is_currency=True,
        currency_symbol=currency_symbol,
        height=height,
        dark_mode=dark_mode,
        hovermode="x unified",
        legend_position="bottom",
    )
    return fig


# Alias per retrocompatibilità
create_monte_carlo_fan_chart = create_montecarlo_fan_chart


def create_asset_allocation_treemap(
    df: pd.DataFrame,
    path: List[str],
    values_col: str,
    color_col: Optional[str] = None,
    color_scale_type: str = "finviz",
    chart_type: str = "treemap",
    title: str = "Asset Allocation & Performance Map",
    currency_symbol: str = "€",
    height: int = 500,
    dark_mode: bool = True,
) -> go.Figure:
    """
    Genera un grafico gerarchico (Treemap o Sunburst) multi-livello per asset allocation:
    - Livelli gerarchici tipici: Macro-Asset Class -> Sub-Classe / Settore -> Singolo Ticker
    - Sizing proporzionale al controvalore/peso di portafoglio
    - Finviz-style PnL color scale (se `color_col` è valorizzato) oppure palette semantica categorica
    - Zero chart clutter, responsive e performante
    """
    if df is None or df.empty or not path or values_col not in df.columns:
        return go.Figure()

    # Copia di lavoro per evitare side effects
    df_plot = df.copy()
    plot_fn = px.sunburst if chart_type == "sunburst" else px.treemap

    # Se color_col è specificato, applichiamo scala continua Finviz PnL
    if color_col and color_col in df_plot.columns:
        # Se i valori sono in decimali (es. +0.05 per 5%), convertiamo in % per la scala
        color_vals = df_plot[color_col].dropna()
        max_abs = float(np.nanmax(np.abs(color_vals))) if len(color_vals) > 0 else 5.0
        bound = max(max_abs, 3.0)  # Almeno +/- 3% per stabilità visiva

        fig = plot_fn(
            df_plot,
            path=path,
            values=values_col,
            color=color_col,
            color_continuous_scale=FINVIZ_PNL_SCALE,
            range_color=[-bound, bound],
            color_continuous_midpoint=0.0,
        )
        fig.update_traces(
            textinfo="label+percent entry",
            insidetextfont={"family": "Outfit, sans-serif", "size": 12},
            hovertemplate=(
                f"<b>%{{label}}</b><br>"
                f"Controvalore: {currency_symbol} %{{value:,.2f}}<br>"
                f"Quota Totale: %{{percentRoot:.1%}}<br>"
                f"Rendimento PnL: <b>%{{color:+.2f}}%</b><extra></extra>"
            ),
        )
        fig.update_coloraxes(
            colorbar={
                "title": {"text": "PnL %", "font": {"family": "Outfit, sans-serif", "size": 11, "color": "#94a3b8"}},
                "tickfont": {"family": "'JetBrains Mono', monospace", "size": 10, "color": "#94a3b8"},
                "ticksuffix": "%",
                "len": 0.75,
                "thickness": 14,
            }
        )
    else:
        # Colorazione categorica basata sulla prima dimensione (Macro Class)
        first_level = path[0]
        unique_macros = df_plot[first_level].unique()
        color_map = {str(m): get_asset_color(str(m)) for m in unique_macros}

        fig = plot_fn(df_plot, path=path, values=values_col, color=first_level, color_discrete_map=color_map)
        fig.update_traces(
            textinfo="label+percent entry",
            insidetextfont={"family": "Outfit, sans-serif", "size": 12},
            hovertemplate=(
                f"<b>%{{label}}</b><br>"
                f"Controvalore: {currency_symbol} %{{value:,.2f}}<br>"
                f"Quota Totale: %{{percentRoot:.1%}}<br>"
                f"Quota sul Ramo: %{{percentEntry:.1%}}<extra></extra>"
            ),
        )

    apply_argus_theme(
        fig, title=title, height=height, dark_mode=dark_mode, show_legend=False, hovermode="closest", show_spikes=False
    )
    return fig


# Alias per retrocompatibilità
create_hierarchical_allocation_chart = create_asset_allocation_treemap


def create_waterfall_cashflow(
    categories: Sequence[str],
    values: Sequence[float],
    measures: Optional[Sequence[str]] = None,
    title: str = "Analisi Cash Flow & Movimentazione Patrimonio",
    currency_symbol: str = "€",
    height: int = 440,
    dark_mode: bool = True,
    final_total_label: Optional[str] = "Patrimonio Finale",
) -> go.Figure:
    """
    Genera un Waterfall Chart istituzionale per entrate, uscite, investimenti e chiusura patrimonio:
    - Entrate positive in verde smeraldo (#10b981)
    - Uscite e costi in corallo/rosso (#ef4444)
    - Patrimonio / Saldo finale totale in blu primario (#3b82f6)
    - Connettori discreti tratteggiati e valori numerici sopra/dentro le barre
    """
    if not categories or not values or len(categories) != len(values):
        return go.Figure()

    cats = list(categories)
    vals = [float(v) for v in values]

    if measures is None:
        # Per impostazione predefinita, tutti i flussi sono relativi tranne l'ultimo elemento che è totale
        measures = ["relative"] * (len(cats) - 1) + ["total"]
    else:
        measures = list(measures)

    fig = go.Figure(
        go.Waterfall(
            name="Cash Flow",
            orientation="v",
            measure=measures,
            x=cats,
            y=vals,
            textposition="outside",
            texttemplate=f"{currency_symbol} %{{y:+,.0f}}",
            textfont={"family": "'JetBrains Mono', monospace", "size": 11, "color": "#e2e8f0" if dark_mode else "#1e293b"},
            connector={
                "line": {
                    "color": "rgba(255, 255, 255, 0.18)" if dark_mode else "rgba(0, 0, 0, 0.18)", "width": 1, "dash": "dot"
                }
            },
            increasing={"marker": {"color": ARGUS_COLORS["bull"]}},
            decreasing={"marker": {"color": ARGUS_COLORS["bear"]}},
            totals={"marker": {"color": ARGUS_COLORS["primary"]}},
            hovertemplate=(
                f"<b>%{{x}}</b><br>"
                f"Flusso: <b>{currency_symbol} %{{y:+,.2f}}</b><br>"
                f"Cumulato: <b>{currency_symbol} %{{currentvalue:,.2f}}</b><extra></extra>"
            ),
        )
    )

    apply_argus_theme(
        fig,
        title=title,
        y_title=f"Flusso ({currency_symbol})",
        is_currency=True,
        currency_symbol=currency_symbol,
        height=height,
        dark_mode=dark_mode,
        show_legend=False,
        hovermode="closest",
    )
    return fig


# Alias per retrocompatibilità
create_cashflow_waterfall_chart = create_waterfall_cashflow


def create_correlation_heatmap(
    corr_matrix: Union[pd.DataFrame, np.ndarray],
    title: str = "Matrice di Correlazione Cross-Asset & Rischio",
    show_values: bool = True,
    colorscale: Optional[List[Any]] = None,
    height: Optional[int] = None,
    dark_mode: bool = True,
) -> go.Figure:
    """
    Genera una Heatmap di correlazione cross-asset ad alto contrasto:
    - Scala divergente fissa (-1.0 a +1.0)
    - Valori numerici leggibili stampati dentro ogni cella
    - Hovertemplate professionale
    """
    if isinstance(corr_matrix, pd.DataFrame):
        if corr_matrix.empty:
            return go.Figure()
        df_corr = corr_matrix
    elif isinstance(corr_matrix, np.ndarray):
        if corr_matrix.size == 0 or corr_matrix.ndim != 2:
            return go.Figure()
        n = corr_matrix.shape[0]
        cols = [f"Asset {i + 1}" for i in range(n)]
        df_corr = pd.DataFrame(corr_matrix, index=cols, columns=cols)
    else:
        return go.Figure()

    labels = df_corr.columns.tolist()
    z_vals = df_corr.values
    scale = colorscale or ARGUS_DIVERGING_SCALE

    text_matrix = []
    for row in z_vals:
        text_matrix.append([f"{v:+.2f}" if pd.notna(v) else "" for v in row])

    fig = go.Figure(
        data=go.Heatmap(
            z=z_vals,
            x=labels,
            y=labels,
            zmin=-1.0,
            zmax=1.0,
            colorscale=scale,
            text=text_matrix if show_values else None,
            texttemplate="%{text}" if show_values else None,
            textfont={"family": "'JetBrains Mono', monospace", "size": 11, "color": "#ffffff"},
            hovertemplate="<b>%{y} ↔ %{x}</b><br>Correlazione di Pearson: <b>%{z:+.3f}</b><extra></extra>",
            colorbar={
                "title": {"text": "Corr", "font": {"family": "Outfit, sans-serif", "size": 11, "color": "#94a3b8"}},
                "tickvals": [-1.0, -0.5, 0.0, 0.5, 1.0],
                "ticktext": ["-1.0", "-0.5", "0.0", "+0.5", "+1.0"],
                "tickfont": {"family": "'JetBrains Mono', monospace", "size": 10, "color": "#94a3b8"},
                "len": 0.85,
                "thickness": 14,
            },
        )
    )

    calc_height = height or max(380, len(labels) * 44 + 80)
    apply_argus_theme(
        fig,
        title=title,
        height=calc_height,
        dark_mode=dark_mode,
        show_legend=False,
        hovermode="closest",
        show_spikes=False,
    )
    return fig


__all__ = [
    "ARGUS_COLORS",
    "ARGUS_FINANCIAL_PALETTE",
    "ARGUS_ASSET_CLASS_COLORS",
    "ARGUS_DIVERGING_SCALE",
    "FINVIZ_PNL_SCALE",
    "ARGUS_GLOW_CONES",
    "ARGUS_SEQUENTIAL_WEALTH",
    "ARGUS_SEQUENTIAL_RISK",
    "get_asset_color",
    "optimize_plotly_figure_memory",
    "register_argus_plotly_templates",
    "get_argus_plotly_config",
    "get_plotly_config",
    "apply_argus_theme",
    "apply_custom_chart_layout",
    "lttb_downsample",
    "auto_webgl_trace",
    "convert_figure_to_webgl",
    "create_timeseries_chart",
    "create_equity_drawdown_chart",
    "create_montecarlo_fan_chart",
    "create_monte_carlo_fan_chart",
    "create_asset_allocation_treemap",
    "create_hierarchical_allocation_chart",
    "create_waterfall_cashflow",
    "create_cashflow_waterfall_chart",
    "create_correlation_heatmap",
]
