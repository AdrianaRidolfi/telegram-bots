
from fpdf import FPDF
import os
import json
from html import escape

def generate_pdf(quiz_path: str) -> str:
    with open(quiz_path, encoding="utf-8") as f:
        data = json.load(f)

    file_name = os.path.splitext(os.path.basename(quiz_path))[0]
    pdf_path = f"{file_name}.pdf"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "INEDITE", ln=True, align="C")

    pdf.set_font("Arial", "", 12)

    for i, item in enumerate(data, 1):
        question = escape(item["question"])
        answers = item["answers"]
        correct = item.get("correct_answer") or item.get("correct")

        # Domanda in grassetto
        pdf.set_font("Arial", "B", 12)
        pdf.multi_cell(0, 8, f"{i}. {question}")

        # Risposte
        for ans in answers:
            if ans == correct:
                pdf.set_text_color(0, 128, 0)  # Verde
            else:
                pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", "", 12)
            pdf.multi_cell(0, 8, f"- {ans}")

        pdf.ln(2)

    pdf.output(pdf_path)
    return pdf_path
