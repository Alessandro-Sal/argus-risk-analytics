import pytest
import pandas as pd
from core.tax_engine import compute_tax_and_harvesting, get_asset_tax_rate

def test_get_asset_tax_rate_edge_cases():
    assert get_asset_tax_rate("bond", "BTP") == 0.125
    assert get_asset_tax_rate("BTP") == 0.125
    assert get_asset_tax_rate("stock", "AAPL") == 0.26
    assert get_asset_tax_rate("crypto", "BTC") == 0.26
    assert get_asset_tax_rate("unknown_asset_type") == 0.26

def test_compute_tax_and_harvesting_empty():
    dummy_results = {"positions": pd.DataFrame()}
    res = compute_tax_and_harvesting(dummy_results)
    assert res is not None
    assert "total_taxable_gains" in res or "harvesting_opportunities" in res

