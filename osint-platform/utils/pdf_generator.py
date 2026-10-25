import re
import io
from fpdf import FPDF, XPos, YPos


class OSINTReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(0, 180, 150)
        self.cell(0, 10, "OSINT AI - Threat Intelligence Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.set_draw_color(0, 180, 150)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}} | CONFIDENTIAL", align="C")

    def add_section(self, title, content):
        self.add_page()
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(0, 180, 150)
        self.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(40, 40, 40)
        cleaned = re.sub(r'[^\x00-\x7F]+', ' ', content)
        cleaned = cleaned.replace('**', '').replace('##', '').replace('###', '').replace('#', '')
        cleaned = cleaned.replace('`', '').replace('---', '---')
        for line in cleaned.split('\n'):
            line = line.strip()
            if not line:
                self.ln(2)
                continue
            self.multi_cell(0, 5, line)


# FIX (was dead/broken): run_osint_audit returns agent-keyed results
# (aria/raven/vulcan/cipher/oracle), but generate_pdf previously looked
# up legacy task keys (final_report/domain_recon/...) that never exist,
# so a real report exported as an empty PDF. Map the real keys here.
# Architecture unchanged: same function, same sections, correct source.
SECTION_AGENT_KEYS = [
    ("Executive Summary", "oracle"),
    ("Domain Reconnaissance", "aria"),
    ("Threat Intelligence", "raven"),
    ("Attack Surface Analysis", "vulcan"),
    ("Email OSINT", "cipher"),
]


def generate_pdf(results: dict) -> bytes:
    pdf = OSINTReportPDF()
    pdf.alias_nb_pages()
    for title, agent_key in SECTION_AGENT_KEYS:
        content = results.get(agent_key, "")
        if content:
            pdf.add_section(title, content)
    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer.getvalue()
