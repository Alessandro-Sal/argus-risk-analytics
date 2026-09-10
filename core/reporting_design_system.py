"""
ARGUS — Financial Reporting Design System
Core Module: Institutional Visual Identity & Memory-Safe Layout Components
Unified across PDF (ReportLab) and Excel (XlsxWriter/OpenPyXL).
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# ── 1. OBSIDIAN SOVEREIGN DESIGN TOKEN PALETTE ─────────────────

@dataclass(frozen=True)
class InstitutionalPalette:
    """Palette cromatiche e token standardizzati per reportistica Family Office & Private Banking."""
    # Colori Fondamentali
    PRIMARY_NAVY: str = "#0F172A"       # Midnight Slate (Titoli primari, card header)
    SECONDARY_SLATE: str = "#1E293B"    # Slate 800 (Header sezioni secondarie)
    ACCENT_EMERALD: str = "#059669"     # Emerald Green (Patrimonio Netto, rendimenti positivi)
    ACCENT_CRIMSON: str = "#DC2626"     # Crimson Red (Drawdown, perdite, alert VaR)
    ACCENT_AMBER: str = "#D97706"       # Amber Gold (Illiquidi, attenzione, inflazione)
    ACCENT_ROYAL: str = "#2563EB"       # Classic Blue (Investimenti liquidi, benchmark)
    
    # Sfondi & Griglie
    BG_PAGE: str = "#FFFFFF"            # Bianco puro
    BG_CARD: str = "#F8FAFC"            # Slate 50 (Sfondo box e KPI pills)
    BG_ZEBRA: str = "#F1F5F9"           # Slate 100 (Righe alternate tabelle)
    BORDER_LIGHT: str = "#E2E8F0"       # Slate 200 (Bordi griglie e divisori)
    
    # Tipografia
    TEXT_DARK: str = "#0F172A"          # Testo principale
    TEXT_MUTED: str = "#64748B"         # Testo secondario, note fiduciarie
    TEXT_LIGHT: str = "#FFFFFF"         # Testo bianco su header scuri


# ── 2. REPORTLAB INSTITUTIONAL NUMBERED CANVAS ─────────────────

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line, Group
    from reportlab.graphics.charts.piecharts import Pie
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


if HAS_REPORTLAB:
    class InstitutionalNumberedCanvas(canvas.Canvas):
        """
        Two-pass canvas per la generazione automatica di:
        1. Intestazione fiduciaria continua (Running Header)
        2. Numerazione dinamica 'Pagina X di Y' (Running Footer)
        3. Dicitura di riservatezza, marcatura temporale ISO e sigillo crittografico Merkle Tree
        """
        merkle_seal: Optional[str] = None

        def __init__(self, *args, **kwargs):
            if "merkle_seal" in kwargs:
                self.merkle_seal = kwargs.pop("merkle_seal")
            super(InstitutionalNumberedCanvas, self).__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_decorations(num_pages)
                super(InstitutionalNumberedCanvas, self).showPage()
            super(InstitutionalNumberedCanvas, self).save()

        def draw_page_decorations(self, page_count: int):
            self.saveState()
            page_w, page_h = A4
            
            # Running Header (pagine successive alla copertina o tutte se single-sheet)
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(colors.HexColor(InstitutionalPalette.PRIMARY_NAVY))
            self.drawString(32, page_h - 26, "ARGUS RISK & WEALTH ANALYTICS")
            
            self.setFont("Helvetica", 7.0)
            self.setFillColor(colors.HexColor(InstitutionalPalette.TEXT_MUTED))
            now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
            self.drawRightString(page_w - 32, page_h - 26, f"EXECUTIVE INSTITUTIONAL FACTSHEET  •  {now_str}")
            
            # Linea sottile divisoria superiore
            self.setStrokeColor(colors.HexColor(InstitutionalPalette.BORDER_LIGHT))
            self.setLineWidth(0.5)
            self.line(32, page_h - 32, page_w - 32, page_h - 32)

            # Running Footer con eventuale Merkle Seal
            self.line(32, 34, page_w - 32, 34)
            self.setFont("Helvetica", 6.5)
            self.setFillColor(colors.HexColor(InstitutionalPalette.TEXT_MUTED))
            
            seal_info = f" • MERKLE SEAL: {self.merkle_seal[:16]}..." if self.merkle_seal else ""
            self.drawString(32, 22, f"STRETTAMENTE RISERVATO — AD ESCLUSIVO USO FIDUCIARIO / PRIVATE BANKING (Art. 24-25 MiFID II){seal_info}")
            self.drawRightString(page_w - 32, 22, f"Pagina {self._pageNumber} di {page_count}")
            
            self.restoreState()

    def get_institutional_canvas_with_merkle_seal(merkle_root_hash: str):
        """Genera una classe canvas dinamica con Merkle Root integrato nel running footer."""
        class SealedCanvas(InstitutionalNumberedCanvas):
            merkle_seal = merkle_root_hash
        return SealedCanvas


    def get_institutional_reportlab_styles() -> Dict[str, ParagraphStyle]:
        """Restituisce il set completo di stili tipografici istituzionali ReportLab."""
        base_styles = getSampleStyleSheet()
        p = InstitutionalPalette

        styles = {
            "DocTitle": ParagraphStyle(
                "DocTitle",
                parent=base_styles["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=18,
                leading=22,
                textColor=colors.HexColor(p.PRIMARY_NAVY),
                spaceAfter=3
            ),
            "DocSubTitle": ParagraphStyle(
                "DocSubTitle",
                parent=base_styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                leading=12,
                textColor=colors.HexColor(p.TEXT_MUTED),
                spaceAfter=12
            ),
            "SectionTitle": ParagraphStyle(
                "SectionTitle",
                parent=base_styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=14,
                textColor=colors.HexColor(p.PRIMARY_NAVY),
                spaceBefore=8,
                spaceAfter=4
            ),
            "KpiLabel": ParagraphStyle(
                "KpiLabel",
                parent=base_styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7,
                leading=9,
                textColor=colors.HexColor(p.TEXT_MUTED),
                alignment=1  # Centrato
            ),
            "KpiValue": ParagraphStyle(
                "KpiValue",
                parent=base_styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=15,
                textColor=colors.HexColor(p.PRIMARY_NAVY),
                alignment=1
            ),
            "KpiValueEmerald": ParagraphStyle(
                "KpiValueEmerald",
                parent=base_styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=15,
                textColor=colors.HexColor(p.ACCENT_EMERALD),
                alignment=1
            ),
            "TableHeader": ParagraphStyle(
                "TableHeader",
                parent=base_styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9.5,
                textColor=colors.white,
                alignment=1
            ),
            "TableHeaderLeft": ParagraphStyle(
                "TableHeaderLeft",
                parent=base_styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9.5,
                textColor=colors.white,
                alignment=0
            ),
            "TableCell": ParagraphStyle(
                "TableCell",
                parent=base_styles["Normal"],
                fontName="Helvetica",
                fontSize=7.5,
                leading=9.5,
                textColor=colors.HexColor(p.TEXT_DARK)
            ),
            "TableCellBold": ParagraphStyle(
                "TableCellBold",
                parent=base_styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9.5,
                textColor=colors.HexColor(p.TEXT_DARK)
            ),
            "TableCellRight": ParagraphStyle(
                "TableCellRight",
                parent=base_styles["Normal"],
                fontName="Helvetica",
                fontSize=7.5,
                leading=9.5,
                textColor=colors.HexColor(p.TEXT_DARK),
                alignment=2
            ),
            "Disclaimer": ParagraphStyle(
                "Disclaimer",
                parent=base_styles["Normal"],
                fontName="Helvetica-Oblique",
                fontSize=6.5,
                leading=8.5,
                textColor=colors.HexColor(p.TEXT_MUTED),
                spaceBefore=6
            )
        }
        return styles


    def create_vector_donut_chart(
        data: List[Tuple[str, float, str]], 
        width: float = 240, 
        height: float = 120
    ) -> Drawing:
        """
        Genera un donut chart vettoriale puro tramite ReportLab Shapes.
        Zero memory leak: nessun processo esterno, nessun handle matplotlib/kaleido.
        """
        d = Drawing(width, height)
        if not data:
            return d

        total = sum(item[1] for item in data)
        if total <= 0:
            return d

        pie = Pie()
        pie.x = 10
        pie.y = 10
        pie.width = 100
        pie.height = 100
        pie.data = [item[1] for item in data]
        pie.sideLabels = False

        for i, item in enumerate(data):
            pie.slices[i].fillColor = colors.HexColor(item[2])
            pie.slices[i].strokeColor = colors.white
            pie.slices[i].strokeWidth = 1.0

        d.add(pie)

        # Buco centrale (Donut effect)
        hole = Circle(60, 60, 24)
        hole.fillColor = colors.white
        hole.strokeColor = colors.HexColor(InstitutionalPalette.BORDER_LIGHT)
        hole.strokeWidth = 0.5
        d.add(hole)

        # Legenda affiancata
        leg_x = 125
        leg_y = height - 20
        for item in data:
            pct = (item[1] / total * 100.0) if total > 0 else 0.0
            # Indicatore cromatico
            sq = Rect(leg_x, leg_y - 2, 7, 7)
            sq.fillColor = colors.HexColor(item[2])
            sq.strokeColor = None
            d.add(sq)
            # Etichetta
            lbl = f"{item[0]}: {pct:.1f}%"
            txt = String(leg_x + 12, leg_y - 1, lbl, fontName="Helvetica", fontSize=7, fillColor=colors.HexColor(InstitutionalPalette.TEXT_DARK))
            d.add(txt)
            leg_y -= 14

        return d
