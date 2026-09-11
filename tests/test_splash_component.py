"""
Unit test per components/splash.py - Redesign Splash Screen & Bootloader Istituzionale
"""
import streamlit as st
from unittest.mock import MagicMock, patch
from components.splash import (
    render_splash_screen,
    get_argus_vector_logo_svg,
    render_splash_html,
    auto_collapse_sidebar,
    auto_expand_sidebar,
)


def test_splash_screen_bypass_when_already_initialized():
    """Verifica che a sessione gia inizializzata render_splash_screen ritorni False istantaneamente."""
    st.session_state.clear()
    st.session_state["_app_initialized"] = True
    result = render_splash_screen(force_show=False)
    assert result is False


def test_splash_screen_bypass_via_query_params():
    """Verifica che il parametro skip_splash consenta il bypass immediato."""
    st.session_state.clear()
    with patch.object(st, "query_params", {"skip_splash": "1"}):
        result = render_splash_screen()
        assert result is False
        assert st.session_state.get("_app_initialized") is True
        assert st.session_state.get("splash_dismissed") is True


def test_splash_screen_cold_boot_renders_and_returns_true():
    """Verifica che al primo avvio assoluto render_splash_screen ritorni True per bloccare con st.stop()."""
    st.session_state.clear()
    with patch("streamlit.markdown") as mock_markdown, patch("streamlit.columns") as mock_columns, patch("streamlit.button", return_value=False), patch("streamlit.components.v1.html"):
        c1, c2 = MagicMock(), MagicMock()
        mock_columns.return_value = (c1, c2)
        result = render_splash_screen()
        assert result is True
        assert mock_markdown.called


def test_splash_screen_force_show_returns_true():
    """Verifica che force_show=True riapra lo splash anche se gia inizializzato."""
    st.session_state.clear()
    st.session_state["_app_initialized"] = True
    with patch("streamlit.markdown") as mock_markdown, patch("streamlit.columns") as mock_columns, patch("streamlit.button", return_value=False), patch("streamlit.components.v1.html"):
        c1, c2 = MagicMock(), MagicMock()
        mock_columns.return_value = (c1, c2)
        result = render_splash_screen(force_show=True)
        assert result is True


def test_splash_screen_button_click_enters_risk():
    """Verifica che il click sul pulsante Risk Analytics imposti i flag e chiami rerun()."""
    st.session_state.clear()
    def fake_button(label, **kwargs):
        if "btn_splash_risk" in kwargs.get("key", ""):
            return True
        return False

    with patch("streamlit.markdown"), patch("streamlit.columns") as mock_columns, patch("streamlit.button", side_effect=fake_button), patch("streamlit.rerun") as mock_rerun, patch("streamlit.components.v1.html"):
        c1, c2 = MagicMock(), MagicMock()
        mock_columns.return_value = (c1, c2)
        result = render_splash_screen()
        assert st.session_state.get("_app_initialized") is True
        assert st.session_state.get("splash_dismissed") is True
        assert st.session_state.get("argus_portal_mode") == "📊 Risk Analytics"
        assert mock_rerun.called


def test_splash_screen_button_click_enters_wealth():
    """Verifica che il click sul pulsante Wealth Management imposti i flag e chiami switch_page()."""
    st.session_state.clear()
    def fake_button(label, **kwargs):
        if "btn_splash_wealth" in kwargs.get("key", ""):
            return True
        return False

    with patch("streamlit.markdown"), patch("streamlit.columns") as mock_columns, patch("streamlit.button", side_effect=fake_button), patch("streamlit.switch_page") as mock_switch, patch("streamlit.components.v1.html"):
        c1, c2 = MagicMock(), MagicMock()
        mock_columns.return_value = (c1, c2)
        result = render_splash_screen()
        assert st.session_state.get("_app_initialized") is True
        assert st.session_state.get("splash_dismissed") is True
        assert st.session_state.get("argus_portal_mode") == "🏛️ Wealth Management"
        assert mock_switch.called


def test_splash_screen_svg_and_html_generation():
    """Verifica la generazione corretta di SVG vettoriale e frame HTML."""
    svg = get_argus_vector_logo_svg(size=130, accent_color="#f59e0b")
    assert "<svg" in svg
    assert "splash-logo-svg" in svg
    assert "#f59e0b" in svg

    html = render_splash_html(
        app_title="ARGUS TEST",
        subtitle="TEST SUBTITLE",
        version_tag="v9.0.0",
        current_status="Testing status...",
        progress_pct=50,
        accent_color="#f59e0b",
        is_fading_out=False,
        show_skip=True,
    )
    assert "argus-splash-root" in html
    assert "ARGUS TEST" in html
    assert "Testing status..." in html
    assert "50%" in html
    assert "Salta introduzione" in html


def test_sidebar_auto_collapse_and_expand_functions():
    """Verifica che le funzioni di auto-collapse ed auto-expand non sollevino eccezioni."""
    with patch("streamlit.components.v1.html") as mock_html:
        auto_collapse_sidebar()
        assert mock_html.called

    with patch("streamlit.components.v1.html") as mock_html:
        auto_expand_sidebar()
        assert mock_html.called
