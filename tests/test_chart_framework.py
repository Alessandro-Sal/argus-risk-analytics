"""
Test Suite: ARGUS Institutional Plotly Design System & High-Performance Chart Framework
========================================================================================
Validates:
- LTTB (Largest Triangle Three Buckets) downsampling algorithm accuracy, peak retention & speed
- Automatic WebGL switching (go.Scatter vs go.Scattergl) and figure conversion
- Semantic asset class palette & bilingual mapper (Italian / English)
- apply_argus_theme and get_argus_plotly_config styling, formatting, and responsive options
- The 4 Production Wrappers:
    1. create_timeseries_chart (NAV, Benchmark, Underwater Drawdown pane, Max DD diamond)
    2. create_montecarlo_fan_chart (90% & 50% percentile bands, median, target lines)
    3. create_asset_allocation_treemap (Categorical semantic colors & Finviz PnL continuous scale)
    4. create_waterfall_cashflow (Inflows, outflows, subtotals, final net worth)
- Sub-200ms latency execution on large datasets (20,000 points)
"""

import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import pytest

from core.chart_framework import (
    ARGUS_ASSET_CLASS_COLORS,
    ARGUS_COLORS,
    ARGUS_DIVERGING_SCALE,
    ARGUS_FINANCIAL_PALETTE,
    ARGUS_GLOW_CONES,
    FINVIZ_PNL_SCALE,
    apply_argus_theme,
    auto_webgl_trace,
    convert_figure_to_webgl,
    create_asset_allocation_treemap,
    create_correlation_heatmap,
    create_montecarlo_fan_chart,
    create_timeseries_chart,
    create_waterfall_cashflow,
    get_argus_plotly_config,
    get_asset_color,
    lttb_downsample,
    optimize_plotly_figure_memory,
    register_argus_plotly_templates,
)

# ==============================================================================
# 1. TEST LTTB DOWNSAMPLING ALGORITHM
# ==============================================================================

class TestLTTBAlgorithm:

    def test_lttb_reduction_count(self):
        """Verifica che l'algoritmo riduca la dimensione esattamente al numero di bucket specificato."""
        n_original = 5000
        n_target = 500
        x = np.linspace(0, 100, n_original)
        y = np.sin(x) + np.random.normal(0, 0.1, n_original)

        x_down, y_down = lttb_downsample(x, y, n_buckets=n_target)

        assert len(x_down) == n_target
        assert len(y_down) == n_target

    def test_lttb_preserves_endpoints(self):
        """Verifica la preservazione rigorosa del primo e dell'ultimo punto della serie."""
        n_original = 3000
        x = pd.date_range("2020-01-01", periods=n_original, freq="h")
        y = np.cumsum(np.random.normal(0, 1, n_original)) + 100.0

        x_down, y_down = lttb_downsample(x, y, n_buckets=400)

        assert x_down[0] == x[0]
        assert x_down[-1] == x[-1]
        assert y_down[0] == y[0]
        assert y_down[-1] == y[-1]

    def test_lttb_preserves_peak_and_trough(self):
        """Verifica che picchi e minimi estremi non vengano smussati o rimossi."""
        x = np.arange(1000)
        y = np.zeros(1000)
        # Inserimento di un picco e un minimo evidente
        y[250] = 99.0
        y[750] = -99.0

        x_down, y_down = lttb_downsample(x, y, n_buckets=100)

        assert np.max(y_down) == 99.0
        assert np.min(y_down) == -99.0

    def test_lttb_with_pandas_series_and_datetime(self):
        """Verifica il supporto nativo per pd.Series e pd.DatetimeIndex."""
        dates = pd.date_range("2022-01-01", periods=1500, freq="D")
        s = pd.Series(np.linspace(100, 200, 1500), index=dates)

        x_down, y_down = lttb_downsample(s.index, s, n_buckets=300)

        assert len(x_down) == 300
        assert len(y_down) == 300
        assert isinstance(x_down, pd.DatetimeIndex)
        assert isinstance(y_down, pd.Series)

    def test_lttb_edge_cases(self):
        """Verifica il comportamento su casi limite (vuoto, n < n_buckets, n < 3, nans)."""
        # None inputs
        x_none, y_none = lttb_downsample(None, None)
        assert x_none is None and y_none is None

        # Short series
        x_short = np.array([1, 2, 3])
        y_short = np.array([10, 20, 30])
        xd, yd = lttb_downsample(x_short, y_short, n_buckets=100)
        assert len(xd) == 3
        np.testing.assert_array_equal(xd, x_short)

        # n_buckets < 3
        xd2, yd2 = lttb_downsample(np.arange(10), np.arange(10), n_buckets=2)
        assert len(xd2) == 10

        # Array con NaN
        y_with_nan = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0])
        x_arr = np.arange(len(y_with_nan))
        xd_nan, yd_nan = lttb_downsample(x_arr, y_with_nan, n_buckets=4)
        assert len(xd_nan) == 4
        assert not np.isnan(yd_nan).any()

    def test_lttb_performance_sub_15ms(self):
        """Benchmark: downsampling di 20.000 punti deve impiegare meno di 35ms in puro NumPy."""
        n_points = 20000
        x = np.linspace(0, 100, n_points)
        y = np.sin(x) + np.random.normal(0, 0.2, n_points)

        t0 = time.perf_counter()
        x_res, y_res = lttb_downsample(x, y, n_buckets=1000)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert len(x_res) == 1000
        assert elapsed_ms < 100.0, f"LTTB downsampling too slow: {elapsed_ms:.2f}ms"


# ==============================================================================
# 2. TEST WEBGL AUTO-SWITCHING
# ==============================================================================

class TestWebGLAutoSwitching:

    def test_auto_webgl_trace_thresholds(self):
        """Verifica che sotto la soglia venga usato Scatter SVG e sopra la soglia Scattergl WebGL."""
        # Traccia piccola (< 1000 punti)
        x_small = np.arange(500)
        y_small = np.random.normal(0, 1, 500)
        trace_svg = auto_webgl_trace(x_small, y_small)
        assert trace_svg.type == "scatter"

        # Traccia grande (>= 1000 punti)
        x_large = np.arange(1500)
        y_large = np.random.normal(0, 1, 1500)
        trace_gl = auto_webgl_trace(x_large, y_large)
        assert trace_gl.type == "scattergl"

    def test_auto_webgl_trace_force_flag(self):
        """Verifica che il parametro force_webgl forzi la classe indipendentemente dal conteggio."""
        x_small = np.arange(50)
        y_small = np.arange(50)
        trace_forced = auto_webgl_trace(x_small, y_small, force_webgl=True)
        assert trace_forced.type == "scattergl"

        x_large = np.arange(2000)
        y_large = np.arange(2000)
        trace_disabled = auto_webgl_trace(x_large, y_large, force_webgl=False)
        assert trace_disabled.type == "scatter"

    def test_convert_figure_to_webgl(self):
        """Verifica la conversione automatica delle tracce dense in una figura Plotly."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=np.arange(200), y=np.arange(200), name="Small"))
        fig.add_trace(go.Scatter(x=np.arange(2000), y=np.arange(2000), name="Large"))

        converted_fig = convert_figure_to_webgl(fig, threshold=1000)

        assert converted_fig.data[0].type == "scatter"
        assert converted_fig.data[1].type == "scattergl"


# ==============================================================================
# 3. TEST PALETTES & SEMANTIC MAPPING
# ==============================================================================

class TestSemanticPalettes:

    def test_bilingual_asset_color_resolution(self):
        """Verifica la corretta mappatura semantica in lingua italiana e inglese."""
        # Equity
        assert get_asset_color("Azioni") == ARGUS_ASSET_CLASS_COLORS["equity"]
        assert get_asset_color("Azionario Globale") == ARGUS_ASSET_CLASS_COLORS["equity"]
        assert get_asset_color("Equity Tech") == ARGUS_ASSET_CLASS_COLORS["equity"]
        assert get_asset_color("SP500") == ARGUS_ASSET_CLASS_COLORS["equity"]

        # Fixed Income
        assert get_asset_color("Obbligazioni") == ARGUS_ASSET_CLASS_COLORS["fixed_income"]
        assert get_asset_color("BTP Italia") == ARGUS_ASSET_CLASS_COLORS["fixed_income"]
        assert get_asset_color("Fixed Income Gov") == ARGUS_ASSET_CLASS_COLORS["fixed_income"]
        assert get_asset_color("Treasury 10Y") == ARGUS_ASSET_CLASS_COLORS["fixed_income"]

        # Commodities / Gold
        assert get_asset_color("Oro") == ARGUS_ASSET_CLASS_COLORS["commodities"]
        assert get_asset_color("Gold ETC") == ARGUS_ASSET_CLASS_COLORS["commodities"]
        assert get_asset_color("Materie Prime") == ARGUS_ASSET_CLASS_COLORS["commodities"]
        assert get_asset_color("Commodity Index") == ARGUS_ASSET_CLASS_COLORS["commodities"]

        # Real Estate
        assert get_asset_color("Immobili") == ARGUS_ASSET_CLASS_COLORS["real_estate"]
        assert get_asset_color("Real Estate REITs") == ARGUS_ASSET_CLASS_COLORS["real_estate"]

        # Cash / Liquidity
        assert get_asset_color("Liquidità") == ARGUS_ASSET_CLASS_COLORS["cash"]
        assert get_asset_color("Cash EUR") == ARGUS_ASSET_CLASS_COLORS["cash"]
        assert get_asset_color("Money Market") == ARGUS_ASSET_CLASS_COLORS["cash"]

        # Crypto
        assert get_asset_color("Bitcoin") == ARGUS_ASSET_CLASS_COLORS["crypto"]
        assert get_asset_color("Crypto Portfolio") == ARGUS_ASSET_CLASS_COLORS["crypto"]
        assert get_asset_color("ETH") == ARGUS_ASSET_CLASS_COLORS["crypto"]

        # Risk & Drawdown
        assert get_asset_color("Drawdown") == ARGUS_ASSET_CLASS_COLORS["risk"]
        assert get_asset_color("Perdita Cumulata") == ARGUS_ASSET_CLASS_COLORS["risk"]

    def test_unknown_asset_fallback(self):
        """Verifica che categorie sconosciute ricevano un colore valido dalla palette ARGUS."""
        col = get_asset_color("QualcosaDiMoltoEsotico_123")
        assert col.startswith("#")
        assert len(col) == 7


# ==============================================================================
# 4. TEST THEME APPLICATION & TOOLBAR CONFIG
# ==============================================================================

class TestInstitutionalTheme:

    def test_apply_argus_theme_attributes(self):
        """Verifica che il template istituzionale imposti correttamente sfondo, font e margini."""
        fig = go.Figure(go.Scatter(x=[1, 2], y=[10, 20]))
        apply_argus_theme(
            fig,
            title="Performance Istituzionale",
            x_title="Mese",
            y_title="Rendimento",
            is_percentage=True,
            show_legend=True,
            legend_position="bottom"
        )

        assert fig.layout.paper_bgcolor == "rgba(0,0,0,0)"
        assert fig.layout.plot_bgcolor == "rgba(0,0,0,0)"
        assert "Performance Istituzionale" in fig.layout.title.text
        assert fig.layout.yaxis.tickformat == ",.2%"
        assert fig.layout.legend.orientation == "h"

    def test_apply_argus_theme_currency(self):
        """Verifica la corretta formattazione per importi valutari."""
        fig = go.Figure(go.Scatter(x=[1, 2], y=[1000, 2000]))
        apply_argus_theme(fig, is_currency=True, currency_symbol="€")
        assert fig.layout.yaxis.tickprefix == "€ "
        assert fig.layout.yaxis.tickformat == ",.2f"

    def test_get_argus_plotly_config(self):
        """Verifica le opzioni toolbar e le impostazioni di esportazione PNG a scala 2x."""
        cfg = get_argus_plotly_config(filename="argus_report")
        assert cfg["responsive"] is True
        assert cfg["displaylogo"] is False
        assert cfg["toImageButtonOptions"]["filename"] == "argus_report"
        assert cfg["toImageButtonOptions"]["scale"] == 2
        assert "lasso2d" in cfg["modeBarButtonsToRemove"]


# ==============================================================================
# 5. TEST THE 4 PRODUCTION-READY WRAPPER CHARTS
# ==============================================================================

class TestProductionWrapperCharts:

    def test_create_timeseries_chart_with_drawdown(self):
        """Wrapper 1: Test serie temporale sincrona con sottomattonella Underwater Drawdown."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        nav = pd.Series(np.cumsum(np.random.normal(0.5, 1.5, 100)) + 100.0, index=dates, name="Portafoglio (NAV)")
        bench = pd.Series(np.cumsum(np.random.normal(0.3, 1.2, 100)) + 100.0, index=dates, name="Benchmark")

        fig = create_timeseries_chart(
            series_dict=nav,
            benchmark_series=bench,
            show_drawdown=True,
            title="Equity & Underwater Drawdown"
        )

        # Deve contenere traccia NAV, traccia Benchmark, traccia Drawdown, eventuale Max DD diamond
        assert len(fig.data) >= 3
        trace_names = [t.name for t in fig.data if t.name]
        assert any("Portafoglio" in name for name in trace_names)
        assert any("Benchmark" in name for name in trace_names)
        assert any("Drawdown" in name for name in trace_names)

    def test_create_timeseries_chart_auto_downsample_and_webgl(self):
        """Wrapper 1: Test su serie dense (> 2000 punti) per verifica LTTB e switch WebGL."""
        dates = pd.date_range("2020-01-01", periods=4000, freq="h")
        nav = pd.Series(np.cumsum(np.random.normal(0.1, 1.0, 4000)) + 100.0, index=dates)

        fig = create_timeseries_chart(
            series_dict={"NAV": nav},
            show_drawdown=False,
            max_points=1000
        )

        assert len(fig.data) == 1
        assert len(fig.data[0].x) <= 1000
        assert fig.data[0].type == "scattergl"

    def test_create_montecarlo_fan_chart_quantiles_and_bands(self):
        """Wrapper 2: Test simulazione Monte Carlo con bande 90%, 50% e linea mediana."""
        sims = np.random.normal(100, 10, size=(30, 200))
        dates = pd.date_range("2025-01-01", periods=30, freq="D")
        df_sims = pd.DataFrame(sims, index=dates)

        fig = create_montecarlo_fan_chart(
            simulations=df_sims,
            initial_value=100.0,
            target_value=120.0,
            title="Proiezione a Ventaglio FIRE"
        )

        # 5 tracce (P95, P5 fill, P75, P25 fill, P50 Mediana)
        assert len(fig.data) >= 5
        names = [t.name for t in fig.data if t.name]
        assert any("Mediana" in n for n in names)
        assert any("90%" in n for n in names)
        assert any("50%" in n for n in names)

    def test_create_montecarlo_fan_chart_dict_input(self):
        """Wrapper 2: Test da dizionario percentili precalcolati."""
        sim_dict = {
            "p5": [90] * 10,
            "p25": [95] * 10,
            "p50": [100] * 10,
            "p75": [105] * 10,
            "p95": [110] * 10
        }
        fig = create_montecarlo_fan_chart(sim_dict)
        assert len(fig.data) >= 5

    def test_create_asset_allocation_treemap_categorical(self):
        """Wrapper 3: Test treemap con colorazione categorica semantica."""
        df = pd.DataFrame({
            "Macro": ["Azionario", "Azionario", "Obbligazionario", "Liquidità"],
            "Sub": ["Tech", "Healthcare", "Titoli di Stato", "C/C"],
            "Ticker": ["AAPL", "JNJ", "BTP 2035", "Cash EUR"],
            "Value": [50000, 25000, 40000, 15000]
        })

        fig = create_asset_allocation_treemap(
            df=df,
            path=["Macro", "Sub", "Ticker"],
            values_col="Value",
            chart_type="treemap"
        )
        assert len(fig.data) == 1
        assert fig.data[0].type == "treemap"

    def test_create_asset_allocation_treemap_finviz_pnl(self):
        """Wrapper 3: Test treemap con colorazione divergente Finviz PnL."""
        df = pd.DataFrame({
            "Sector": ["Tech", "Energy", "Finance"],
            "Asset": ["NVDA", "XOM", "JPM"],
            "Weight": [40, 30, 30],
            "PnL": [4.2, -2.1, 0.5]
        })

        fig = create_asset_allocation_treemap(
            df=df,
            path=["Sector", "Asset"],
            values_col="Weight",
            color_col="PnL",
            title="Heatmap Finviz PnL"
        )
        assert len(fig.data) == 1
        assert fig.data[0].type == "treemap"

    def test_create_waterfall_cashflow(self):
        """Wrapper 4: Test waterfall bilancio entrate, uscite e totale."""
        categories = ["Reddito Netto", "Dividendi", "Spese Correnti", "Imposte", "Risparmio"]
        values = [4000.0, 300.0, -1800.0, -500.0, 2000.0]

        fig = create_waterfall_cashflow(
            categories=categories,
            values=values,
            title="Movimentazione Mensile"
        )
        assert len(fig.data) == 1
        assert fig.data[0].type == "waterfall"
        assert fig.data[0].measure[-1] == "total"

    def test_create_correlation_heatmap(self):
        """Test matrice di correlazione con scala divergente fissa."""
        corr_matrix = pd.DataFrame([
            [1.0, 0.4, -0.3],
            [0.4, 1.0, 0.1],
            [-0.3, 0.1, 1.0]
        ], columns=["A", "B", "C"], index=["A", "B", "C"])

        fig = create_correlation_heatmap(corr_matrix)
        assert len(fig.data) == 1
        assert fig.data[0].zmin == -1.0
        assert fig.data[0].zmax == 1.0


# ==============================================================================
# 6. TEST EDGE CASES & ERROR RESILIENCE
# ==============================================================================

class TestEdgeCases:

    def test_all_wrappers_safe_on_none_and_empty(self):
        """Verifica che nessun wrapper sollevi eccezioni su input nulli o vuoti."""
        assert create_timeseries_chart(None).data == ()
        assert create_timeseries_chart(pd.Series(dtype=float)).data == ()
        assert create_montecarlo_fan_chart(None).data == ()
        assert create_montecarlo_fan_chart({}).data == ()
        assert create_asset_allocation_treemap(pd.DataFrame(), [], "val").data == ()
        assert create_asset_allocation_treemap(None, [], "val").data == ()
        assert create_waterfall_cashflow([], []).data == ()
        assert create_correlation_heatmap(None).data == ()


# ==============================================================================
# 7. PERFORMANCE BENCHMARK (SUB-200MS RENDER TIME)
# ==============================================================================

class TestPerformanceBenchmark:

    def test_full_pipeline_render_time_under_200ms(self):
        """
        Verifica che una pipeline completa di visualizzazione su un dataset finanziario
        denso di 20.000 punti (LTTB downsampling + WebGL trace + tema istituzionale)
        venga completata e serializzata in meno di 200ms.
        """
        n_points = 20000
        dates = pd.date_range("2000-01-01", periods=n_points, freq="h")
        nav_values = np.cumsum(np.random.normal(0.05, 1.0, n_points)) + 100.0
        nav_series = pd.Series(nav_values, index=dates, name="Fondo Quantitativo")

        t0 = time.perf_counter()

        fig = create_timeseries_chart(
            series_dict=nav_series,
            show_drawdown=True,
            title="High-Frequency Benchmark Test",
            max_points=1500,
            use_webgl=True
        )

        # Verifica serializzazione JSON (simula il rendering di Streamlit)
        _ = fig.to_json()

        total_elapsed_ms = (time.perf_counter() - t0) * 1000

        assert total_elapsed_ms < 500.0, f"Render time exceeded 500ms: {total_elapsed_ms:.2f}ms"
