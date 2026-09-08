import pytest
import re
from core.ui_utils import (
    KNOWN_METRICS_KNOWLEDGE_BASE,
    resolve_metric_knowledge,
    format_institutional_5point_html,
    render_metric_info_modal,
    render_info_tooltip,
    metric_card
)

# Perimeter of metrics defined in the implementation plan
PERIMETER_RISK_METRICS = [
    "var_parametric_95",
    "var_parametric_99",
    "var_historical_95",
    "var_historical_99",
    "var_cornish_fisher",
    "var_monte_carlo",
    "cvar_expected_shortfall",
    "garch_volatility",
    "tail_risk_index",
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
    "omega_ratio",
    "information_ratio",
    "treynor_ratio",
    "max_drawdown",
    "ulcer_index",
    "average_drawdown",
    "recovery_time",
    "beta_market",
    "r_squared",
    "alpha_jensen",
    "tracking_error",
    "correlation_distance",
    "hrp_diversification_ratio"
]

PERIMETER_WEALTH_METRICS = [
    "net_worth_consolidated",
    "liquid_net_worth",
    "solvency_ratio",
    "debt_to_asset",
    "savings_rate",
    "emergency_runway",
    "fixed_cost_ratio",
    "swr_fire",
    "fire_number",
    "pension_replacement_rate",
    "pension_gap",
    "pmc_fiscale",
    "zainetto_fiscale",
    "real_net_return"
]

MANDATORY_SECTIONS = [
    "📌 Cos'è",
    "⚙️ Come viene calcolato da ARGUS",
    "📐 Come si calcola",
    "🎯 A cosa serve",
    "📊 Come si legge & Valori Guida",
    "⚠️ Limitazioni & Assunzioni del Modello"
]


def test_perimeter_metrics_registered_in_knowledge_base():
    """Tutte le metriche del perimetro Risk e Wealth devono essere registrate nella Knowledge Base."""
    for key in PERIMETER_RISK_METRICS:
        assert key in KNOWN_METRICS_KNOWLEDGE_BASE, f"Metrica Risk '{key}' non presente in KNOWN_METRICS_KNOWLEDGE_BASE"
    for key in PERIMETER_WEALTH_METRICS:
        assert key in KNOWN_METRICS_KNOWLEDGE_BASE, f"Metrica Wealth '{key}' non presente in KNOWN_METRICS_KNOWLEDGE_BASE"


def test_every_perimeter_metric_has_strict_5_blocks():
    """Ogni metrica del perimetro deve contenere tutti e 5 i blocchi istituzionali obbligatori."""
    all_keys = PERIMETER_RISK_METRICS + PERIMETER_WEALTH_METRICS
    for key in all_keys:
        html = resolve_metric_knowledge(key)
        for sec in MANDATORY_SECTIONS:
            assert sec in html, f"Blocco obbligatorio '{sec}' assente nell'output HTML per la metrica '{key}'"


def test_methodological_accuracy_formulas_and_conventions():
    """Verifica l'accuratezza metodologica e la presenza di formule e parametri corretti."""
    
    # 1. Cornish-Fisher: guard-rails di clamping monotonicità
    cf_html = resolve_metric_knowledge("var_cornish_fisher")
    assert "monotonicit" in cf_html or "[-3.0, 3.0]" in cf_html or "clamping" in cf_html
    assert "z<sub>CF</sub>" in cf_html or "z_CF" in cf_html or "z_{CF}" in cf_html

    # 2. Sortino: semi-deviation divisa per N (e non solo per i negativi)
    sortino_html = resolve_metric_knowledge("sortino_ratio")
    assert "252" in sortino_html
    assert "downside" in sortino_html.lower()

    # 3. GARCH: stazionarietà alpha + beta < 1
    garch_html = resolve_metric_knowledge("garch_volatility")
    assert "&alpha;" in garch_html or "alpha" in garch_html
    assert "&beta;" in garch_html or "beta" in garch_html
    assert "&omega;" in garch_html or "omega" in garch_html
    assert "stazionar" in garch_html

    # 4. HRP: formula distanza di correlazione euclidea
    corr_dist_html = resolve_metric_knowledge("correlation_distance")
    assert "d<sub>ij</sub>" in corr_dist_html or "d_{ij}" in corr_dist_html
    assert "&rho;" in corr_dist_html or "rho" in corr_dist_html

    # 5. Rendimento Reale: Equazione di Fisher
    real_ret_html = resolve_metric_knowledge("real_net_return")
    assert "Fisher" in real_ret_html
    assert "inflazione" in real_ret_html

    # 6. SWR & FIRE: 25x e Trinity study
    fire_html = resolve_metric_knowledge("fire_number")
    assert "25" in fire_html or "SWR" in fire_html


def test_universal_ui_components_callable():
    """Verifica che i nuovi componenti universali riutilizzabili siano callable senza eccezioni."""
    # Test render_metric_info_modal
    render_metric_info_modal("sharpe_ratio", title="Test Sharpe Modal")
    render_metric_info_modal("net_worth_consolidated", title="Test Net Worth Modal")
    
    # Test format_institutional_5point_html con e senza limitations
    html_no_lim = format_institutional_5point_html(
        title="Test Title",
        what_is="What is test",
        how_calc="How calc test",
        why_useful="Why useful test",
        argus_calc="Argus calc test",
        how_to_read="How to read test"
    )
    assert "📌 Cos'è" in html_no_lim
    assert "⚠️ Limitazioni" not in html_no_lim

    html_with_lim = format_institutional_5point_html(
        title="Test Title",
        what_is="What is test",
        how_calc="How calc test",
        why_useful="Why useful test",
        argus_calc="Argus calc test",
        how_to_read="How to read test",
        limitations="Questa è una limitazione metodologica specifica di test."
    )
    assert "📌 Cos'è" in html_with_lim
    assert "⚠️ Limitazioni & Assunzioni del Modello" in html_with_lim


def test_metric_card_renders_with_institutional_knowledge():
    """Verifica che metric_card incorpori la nuova scheda informativa a 5 blocchi."""
    card_html = metric_card(
        label="Value at Risk 95%",
        value="-1.42%",
        delta="+0.15%",
        positive=True
    )
    # Deve contenere la struttura modale e i blocchi istituzionali
    assert "📌 Cos'è" in card_html
    assert "⚙️ Come viene calcolato da ARGUS" in card_html
    assert "⚠️ Limitazioni & Assunzioni del Modello" in card_html


def test_metric_card_renders_vector_svg_icon_no_unicode_artifact():
    """Verifica che l'icona trigger sia un SVG vettoriale nitido e privo del carattere unicode ⓘ (u24d8)."""
    card_html = metric_card(
        label="Sharpe Ratio",
        value="1.45",
        delta="+0.12",
        positive=True
    )
    # Deve contenere l'icona SVG vettoriale
    assert "<svg" in card_html
    assert 'viewBox="0 0 24 24"' in card_html
    assert "<circle cx=\"12\" cy=\"12\" r=\"10\"" in card_html
    # Non deve più contenere il glifo unicode U+24D8 causa del doppio cerchio / artefatto
    assert "\u24d8" not in card_html
