import io
import pandas as pd
from core.excel_generator import generate_excel_in_memory

def test_generate_excel_in_memory():
    # Mock active positions DataFrame
    df_positions = pd.DataFrame([
        {
            "ticker": "AAPL",
            "asset_class": "Equity",
            "gics_sector": "Technology",
            "qty_net": 10.0,
            "avg_cost": 150.0,
            "last_price": 180.0,
            "current_value": 1800.0,
            "weight_pct": 60.0
        },
        {
            "ticker": "MSFT",
            "asset_class": "Equity",
            "gics_sector": "Technology",
            "qty_net": 5.0,
            "avg_cost": 300.0,
            "last_price": 240.0,
            "current_value": 1200.0,
            "weight_pct": 40.0
        }
    ])
    
    output = generate_excel_in_memory(df_positions)
    
    assert isinstance(output, io.BytesIO)
    bytes_data = output.getvalue()
    
    assert len(bytes_data) > 0
    # Check for zip archive/XLSX signature
    assert bytes_data.startswith(b"PK")
