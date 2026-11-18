import os
import glob
from fpdf import FPDF
from fpdf.enums import XPos, YPos

class CampusPDF(FPDF):
    def __init__(self, doc_title):
        super().__init__()
        self.doc_title = doc_title

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(11, 60, 93)
        self.cell(self.epw, 8, f"PES UNIVERSITY OFFICIAL RECORD | {self.doc_title}", border="B", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(self.epw, 10, f"Page {self.page_no()}", align="C")

def text_to_pdf(txt_path, pdf_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    filename = os.path.basename(txt_path)
    title = filename.replace(".txt", "").replace("_", " ").title()

    pdf = CampusPDF(doc_title=title)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(30, 30, 30)

    for line in text.split("\n"):
        line_clean = line.strip()
        if not line_clean:
            pdf.ln(3)
        elif line_clean.startswith("===") or line_clean.startswith("---"):
            pdf.ln(2)
        elif line_clean.startswith("SECTION") or line_clean.startswith("PES UNIVERSITY"):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(11, 60, 93)
            pdf.multi_cell(pdf.epw, 6, line_clean, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=10)
            pdf.set_text_color(40, 40, 40)
            pdf.ln(1)
        elif any(line_clean.startswith(f"{i}.") for i in range(1, 10)):
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(pdf.epw, 5, line_clean, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=10)
        else:
            pdf.multi_cell(pdf.epw, 5, line_clean, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.output(pdf_path)
    print(f"Generated PDF: {pdf_path}")

def main():
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "documents")
    for txt_file in glob.glob(os.path.join(docs_dir, "*.txt")):
        base_name = os.path.splitext(txt_file)[0]
        pdf_path = f"{base_name}.pdf"
        text_to_pdf(txt_file, pdf_path)

if __name__ == "__main__":
    main()
