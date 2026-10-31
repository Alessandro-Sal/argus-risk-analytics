"""ARGUS — Unified Financial Reporting, Factsheet & Export Architecture."""
from core.reporting.board_pack import ExecutiveBoardPackEngine, generate_executive_board_pack
from core.reporting.csv_exporter import export_all
from core.reporting.db_exporter import save_snapshot_to_db
from core.reporting.design_system import (
    InstitutionalNumberedCanvas,
    InstitutionalPalette,
    create_vector_donut_chart,
    get_institutional_reportlab_styles,
)
from core.reporting.excel import generate_excel_in_memory
from core.reporting.factsheet import FactsheetExportConfig, ModularFactsheetBuilder
from core.reporting.html import generate_interactive_html_report
from core.reporting.pdf import (
    generate_executive_pdf_report,
    generate_institutional_portfolio_factsheet_pdf,
    generate_regulatory_stress_testing_dossier_pdf,
)
from core.reporting.priips import (
    generate_priips_kid_data,
    generate_priips_kid_html,
    generate_priips_kid_pdf,
    render_priips_kid_popover,
)
from core.reporting.quarterly import generate_white_label_quarterly_pdf_report
from core.reporting.report_exporter import (
    generate_cro_institutional_dossier_zip,
    generate_excel_report,
    generate_institutional_audit_dossier,
    generate_pdf_factsheet,
)

__all__ = [
    "InstitutionalPalette",
    "InstitutionalNumberedCanvas",
    "get_institutional_reportlab_styles",
    "create_vector_donut_chart",
    "generate_executive_pdf_report",
    "generate_institutional_portfolio_factsheet_pdf",
    "generate_regulatory_stress_testing_dossier_pdf",
    "generate_white_label_quarterly_pdf_report",
    "generate_excel_in_memory",
    "generate_interactive_html_report",
    "ExecutiveBoardPackEngine",
    "generate_executive_board_pack",
    "FactsheetExportConfig",
    "ModularFactsheetBuilder",
    "generate_priips_kid_data",
    "generate_priips_kid_pdf",
    "generate_priips_kid_html",
    "render_priips_kid_popover",
    "export_all",
    "save_snapshot_to_db",
    "generate_cro_institutional_dossier_zip",
    "generate_excel_report",
    "generate_institutional_audit_dossier",
    "generate_pdf_factsheet",
]
