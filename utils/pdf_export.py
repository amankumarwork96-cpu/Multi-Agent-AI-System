"""
PDF export helper for the final report.
"""

from fpdf import FPDF

def build_report_pdf(report: dict, user_question: str) -> bytes:
    pdf =  FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, "Multi-Agent AI Data Analyst - Report")
    pdf.ln(2)

    pdf.set_font("Helvetica", "I", 11)
    pdf.multi_cell(0, 8, f"Question: {user_question}")
    pdf.ln(1)

    def section_title(text: str) -> None:
        pdf.set_font("Helvetica", "B", 13)
        pdf.multi_cell(0, 8, text)
        pdf.ln(1)

    def body_text(text: str) -> None:
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 7, text)
        pdf.ln(2)

    section_title("Executive Summary")
    body_text(report["executive_summary"])

    section_title("Key Findings")
    for finding in report["key_findings"]:
        body_text(f"- {finding['findings']}")
        pdf.set_font("Helvetica", "I", 10)
        pdf.multi_cell(0, 6, f"  Evidence: {finding['supporting_evidence']}")
        pdf.ln(1)
    

    section_title("Business Recommendations")
    for rec in report["business_recommendations"]:
        body_text(f" - {rec}")
    
    if report.get("limitations"):
        section_title("Limitations")
        for lim in report["limitations"]:
            body_text(f"- {lim}")

    return bytes(pdf.output())