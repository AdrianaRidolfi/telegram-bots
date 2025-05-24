import os
from fpdf import FPDF
import json
from html import escape

QUIZ_FOLDER = "quizzes"
IMAGES_FOLDER = "quizzes/images"

def clean_text(text):
    replacements = {
        '\u201c': '"',  # “
        '\u201d': '"',  # ”
        '\u2018': "'",  # ‘
        '\u2019': "'",  # ’
        '\u2013': '-',  # –
        '\u2014': '-',  # —
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text

def generate_pdf_sync(quiz_path: str) -> str:
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
        question = clean_text(item["question"])
        answers = item["answers"]
        correct = item.get("correct_answer") or item.get("correct")
        image_path = item.get("image")

        pdf.set_font("Arial", "B", 12)
        pdf.multi_cell(0, 8, f"{i}. {escape(question)}")

        if image_path:
            img_full_path = os.path.join(IMAGES_FOLDER, image_path)
            if os.path.exists(img_full_path):
                pdf.image(img_full_path, x=pdf.get_x(), y=pdf.get_y(), w=100)
                pdf.ln(50)  # Spazio dopo immagine

        for ans in answers:
            ans_clean = clean_text(ans)
            if ans == correct:
                pdf.set_text_color(0, 128, 0)
            else:
                pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", "", 12)
            pdf.multi_cell(0, 8, f"- {escape(ans_clean)}")

        pdf.ln(2)

    pdf.output(pdf_path)
    return pdf_path

async def generate_pdf(quiz_file, bot, user_id):
    quiz_path = os.path.join(QUIZ_FOLDER, quiz_file)
    try:
        pdf_path = generate_pdf_sync(quiz_path)
        with open(pdf_path, "rb") as pdf_file:
            await bot.send_document(chat_id=user_id, document=pdf_file, filename=os.path.basename(pdf_path))
    except Exception as e:
        await bot.send_message(chat_id=user_id, text=f"❌ Errore nella generazione o invio del PDF: {e}")
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
