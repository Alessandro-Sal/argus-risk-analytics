import pytest
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from core.ui_utils import (
    register_argus_plotly_templates,
    get_plotly_config,
    apply_custom_chart_layout,
    create_monte_carlo_fan_chart,
    create_correlation_heatmap,
    create_cashflow_waterfall_chart,
    create_equity_drawdown_chart,
    create_hierarchical_allocation_chart,
    ARGUS_COLORS,
    ARGUS_FINANCIAL_PALETTE
)

def test_templates_registered():
    register_argus_plotly_templates()
    assert 'argus_dark' in pio.templates
    assert 'argus_light' in pio.templates
    dark_t = pio.templates['argus_dark']
    assert dark_t.layout.paper_bgcolor == 'rgba(0,0,0,0)'
    assert 'Outfit' in dark_t.layout.font.family

def test_get_plotly_config():
    cfg = get_plotly_config(filename='my_export', display_mode_bar='hover')
    assert cfg['displayModeBar'] == 'hover'
    cfg_always = get_plotly_config(filename='my_export', display_mode_bar='always')
    assert cfg_always['displayModeBar'] is True
    assert cfg['displaylogo'] is False
    assert 'lasso2d' in cfg['modeBarButtonsToRemove']
    assert cfg['toImageButtonOptions']['filename'] == 'my_export'
    assert cfg['toImageButtonOptions']['scale'] == 2


def test_apply_custom_chart_layout():
    fig = go.Figure(go.Scatter(x=[1, 2, 3], y=[10, 20, 30]))
    apply_custom_chart_layout(
        fig,
        title='Test Titolo',
        x_title='Asse X',
        y_title='Asse Y',
        is_percentage=True,
        show_legend=True,
        dark_mode=True
    )
    assert fig.layout.template is not None
    assert 'Test Titolo' in fig.layout.title.text
    assert fig.layout.yaxis.tickformat == ',.2%'

    # Test currency layout
    fig_curr = go.Figure(go.Scatter(x=[1, 2], y=[100, 200]))
    apply_custom_chart_layout(fig_curr, is_currency=True, currency_symbol='$', dark_mode=False)
    assert fig_curr.layout.template is not None
    assert fig_curr.layout.yaxis.tickprefix == '$ '

def test_monte_carlo_fan_chart():
    # Test from DataFrame
    dates = pd.date_range('2025-01-01', periods=20, freq='D')
    sims = np.random.normal(100, 5, size=(20, 50))
    df_sims = pd.DataFrame(sims, index=dates)
    
    fig = create_monte_carlo_fan_chart(
        df_sims,
        initial_value=100.0,
        target_value=110.0,
        title='Monte Carlo Sim'
    )
    assert len(fig.data) >= 5 # p95, p5, p75, p25, p50
    assert any('Mediana' in t.name for t in fig.data if t.name)
    
    # Test from ndarray
    fig_arr = create_monte_carlo_fan_chart(sims, dates=dates)
    assert len(fig_arr.data) >= 5

    # Test from dict
    fig_dict = create_monte_carlo_fan_chart({
        'p5': [90]*10, 'p25': [95]*10, 'p50': [100]*10, 'p75': [105]*10, 'p95': [110]*10
    })
    assert len(fig_dict.data) >= 5

def test_correlation_heatmap():
    corr_df = pd.DataFrame({
        'AAPL': [1.0, 0.45, -0.2],
        'MSFT': [0.45, 1.0, 0.15],
        'BND': [-0.2, 0.15, 1.0]
    }, index=['AAPL', 'MSFT', 'BND'])
    
    fig = create_correlation_heatmap(corr_df, title='Cross-Asset Correlation')
    assert len(fig.data) == 1
    assert fig.data[0].zmin == -1.0
    assert fig.data[0].zmax == 1.0
    assert fig.data[0].colorbar.title.text == 'Corr'

def test_cashflow_waterfall_chart():
    cats = ['Stipendio', 'Affitto', 'Utenze', 'Risparmio Netto']
    vals = [3500.0, -1200.0, -300.0, 2000.0]
    fig = create_cashflow_waterfall_chart(cats, vals, title='Bilancio Mensile')
    assert len(fig.data) == 1
    assert fig.data[0].type == 'waterfall'
    assert fig.data[0].measure[-1] == 'total'

def test_equity_drawdown_chart():
    dates = pd.date_range('2024-01-01', periods=50, freq='D')
    nav = pd.Series(np.cumsum(np.random.normal(1.0, 2.0, size=50)) + 100.0, index=dates)
    bench = pd.Series(np.cumsum(np.random.normal(0.5, 1.5, size=50)) + 100.0, index=dates)
    
    fig = create_equity_drawdown_chart(
        nav_series=nav,
        benchmark_series=bench,
        title='Equity and Drawdown'
    )
    # Should have traces for NAV, Benchmark, Drawdown, and optionally Max DD marker
    assert len(fig.data) >= 3
    assert any('Portafoglio' in t.name for t in fig.data if t.name)
    assert any('Benchmark' in t.name for t in fig.data if t.name)
    assert any('Drawdown' in t.name for t in fig.data if t.name)

def test_hierarchical_allocation_chart():
    df = pd.DataFrame({
        'Macro': ['Azionario', 'Azionario', 'Obbligazionario', 'Liquidita'],
        'Sub': ['Tech', 'Health', 'Gov', 'Cash'],
        'Asset': ['AAPL', 'JNJ', 'BTP 10Y', 'EUR Cash'],
        'Value': [40000, 20000, 30000, 10000]
    })
    
    fig_sun = create_hierarchical_allocation_chart(
        df,
        path=['Macro', 'Sub', 'Asset'],
        values_col='Value',
        chart_type='sunburst'
    )
    assert fig_sun.data[0].type == 'sunburst'
    
    fig_tree = create_hierarchical_allocation_chart(
        df,
        path=['Macro', 'Sub', 'Asset'],
        values_col='Value',
        chart_type='treemap'
    )
    assert fig_tree.data[0].type == 'treemap'

def test_edge_cases():
    assert create_monte_carlo_fan_chart(None).data == ()
    assert create_correlation_heatmap(None).data == ()
    assert create_cashflow_waterfall_chart([], []).data == ()
    assert create_equity_drawdown_chart(pd.Series(dtype=float)).data == ()
    assert create_hierarchical_allocation_chart(pd.DataFrame(), [], 'val').data == ()
