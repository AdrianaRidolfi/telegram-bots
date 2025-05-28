import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import json

QUIZ_FOLDER = "quizzes"
IMAGES_FOLDER = "quizzes/images"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_FOLDER = os.path.join(BASE_DIR, "quizzes", "fonts")
DEJAVU_TTF = os.path.join(FONTS_FOLDER, "DejaVuSans.ttf") 

def clean_text(text):
    replacements = {
        '\u201c': '"',  # “
        '\u201d': '"',  # ”
        '\u2018': "'",  # ‘
        '\u2019': "'",  # ’
        '\u2013': '-',  # –
        '\u2014': '-',  # —
        '&amp;': '&',   # evita entità html comuni
        '&lt;': '<',
        '&gt;': '>',
        '&#x27;': "'",
        '&#39;': "'",
        '&quot;': '"',
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

    # Registro il font
    pdf.add_font('DejaVu', '', DEJAVU_TTF)
    pdf.add_font('DejaVu', 'B', os.path.join(FONTS_FOLDER, "DejaVuSans-Bold.ttf"))

    pdf.set_font("DejaVu", "B", 16)
    # modifica ln=True con new_x e new_y per evitare deprecazione
    pdf.cell(0, 10, "INEDITE", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("DejaVu", "", 12)

    letters = ['A', 'B', 'C', 'D']

    for i, item in enumerate(data, 1):
        question = clean_text(item["question"])
        answers = item["answers"]
        correct = item.get("correct_answer") or item.get("correct")
        image_path = item.get("image")

        pdf.set_font("DejaVu", "B", 12)
        # per evitare "not enough horizontal space" metti larghezza fissa e resetta x
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.w - 2*pdf.l_margin, 8, f"{i}. {question}")

        if image_path:
            img_full_path = os.path.join(IMAGES_FOLDER, image_path)
            if os.path.exists(img_full_path):
                pdf.set_x(pdf.l_margin)
                x = pdf.get_x()
                y = pdf.get_y()
                max_width = pdf.w - 2 * pdf.l_margin
                pdf.image(img_full_path, x=x, y=y, w=min(100, max_width))

        correct_letter = None

        for idx, ans in enumerate(answers):
            ans_clean = clean_text(ans)
            letter = letters[idx]

            if ans == correct:
                pdf.set_text_color(0, 128, 0)  # verde
                correct_letter = letter
            else:
                pdf.set_text_color(0, 0, 0)    # nero

            pdf.set_font("DejaVu", "", 12)
            # stesso fix per le risposte
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.w - 2*pdf.l_margin, 8, f"{letter}. {ans_clean}")

        pdf.ln(1)

        if correct_letter:
            pdf.set_text_color(0, 128, 0)
            pdf.set_font("DejaVu", "B", 12)
            # anche qui cambia ln=True come sopra
            pdf.cell(0, 8, f"Risposta corretta: {correct_letter}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)

        pdf.ln(5)

        

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
