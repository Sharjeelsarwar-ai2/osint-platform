import re
import io
from fpdf import FPDF


class OSINTReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(0, 180, 150)
        self.cell(0, 10, "OSINT AI - Threat Intelligence Report", ln=True, align="C")
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
        self.cell(0, 10, title, ln=True)
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


def generate_pdf(results: dict) -> bytes:
    pdf = OSINTReportPDF()
    pdf.alias_nb_pages()
    sections = [
        ("Executive Summary", results.get("final_report", "")),
        ("Domain Reconnaissance", results.get("domain_recon", "")),
        ("Threat Intelligence", results.get("threat_intel", "")),
        ("Attack Surface Analysis", results.get("attack_surface", "")),
        ("Email OSINT", results.get("email_osint", ""))
    ]
    for title, content in sections:
        if content:
            pdf.add_section(title, content)
    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer.getvalue()