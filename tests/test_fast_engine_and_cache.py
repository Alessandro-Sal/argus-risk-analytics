import time
import pytest
from sqlalchemy import create_engine
from core.fetcher import get_engine, _BOOTSTRAPPED_ENGINES, clear_engine_caches
from core.wealth.wealth_db import (
    get_wealth_portfolios,
    create_wealth_portfolio,
    clear_wealth_portfolios_cache,
    _WEALTH_PROFILES_CACHE,
)


def test_engine_schema_bootstrap_only_runs_once():
    """Verifica che get_engine esegua la scansione DDL/ALTER TABLE una sola volta per engine."""
    clear_engine_caches()
    eng1 = get_engine(offline=True, sqlite_path="data/test_speed_cache.db")
    eng_key = str(getattr(eng1, "url", id(eng1)))
    assert eng_key in _BOOTSTRAPPED_ENGINES

    # Second call should be instantaneous and hit cache
    t0 = time.time()
    eng2 = get_engine(offline=True, sqlite_path="data/test_speed_cache.db")
    elapsed = time.time() - t0
    assert elapsed < 0.05  # sub-50ms
    assert eng2 is not None


def test_wealth_portfolios_in_memory_caching():
    """Verifica che get_wealth_portfolios memorizzi i profili in cache e si invalidi alle modifiche."""
    from sqlalchemy.pool import StaticPool
    clear_wealth_portfolios_cache()
    eng = create_engine("sqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False})

    # First fetch: populates cache
    df1 = get_wealth_portfolios(eng)
    assert not df1.empty
    assert len(_WEALTH_PROFILES_CACHE) > 0

    # Second fetch: instant from cache
    t0 = time.time()
    df2 = get_wealth_portfolios(eng)
    elapsed = time.time() - t0
    assert elapsed < 0.01  # sub-10ms
    assert len(df1) == len(df2)

    # Creating a new portfolio should invalidate cache
    new_pid = create_wealth_portfolio(eng, name="Nuovo Profilo VIP Speed Test")
    assert new_pid is not None
    # Verify cache was invalidated
    assert len(_WEALTH_PROFILES_CACHE) == 0

    # Refetch should now contain the new profile
    df3 = get_wealth_portfolios(eng)
    assert any(df3["name"] == "Nuovo Profilo VIP Speed Test")
