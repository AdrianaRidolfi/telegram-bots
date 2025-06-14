import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import json
from PIL import Image

LINE_HEIGHT = 3.5
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

    # Font
    pdf.add_font('DejaVu', '', DEJAVU_TTF)
    pdf.add_font('DejaVu', 'B', os.path.join(FONTS_FOLDER, "DejaVuSans-Bold.ttf"))

    pdf.set_font("DejaVu", "B", 16)
    title = file_name.replace("_", " ").upper()
    pdf.cell(0, 10, title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("DejaVu", "", 8)
    letters = ['A', 'B', 'C', 'D']

    for i, item in enumerate(data, 1):
        question = clean_text(item["question"])
        answers = item["answers"]
        correct = item.get("correct_answer") or item.get("correct")
        image_path = item.get("image")

        # CALCOLO SPAZIO NECESSARIO PRIMA DI STAMPARE
        question_lines = pdf.get_string_width(question) // (pdf.w - 2 * pdf.l_margin) + 1
        question_height = question_lines * 8 + 2
        answers_height = len(answers) * 10
        image_height = 0

        if image_path:
            img_full_path = os.path.join(IMAGES_FOLDER, image_path)
            if os.path.exists(img_full_path):
                with Image.open(img_full_path) as img:
                    aspect_ratio = img.height / img.width
                    image_height = min(100, pdf.w - 2*pdf.l_margin) * aspect_ratio + 5

        total_needed = question_height + answers_height + image_height + 20

        # Se lo spazio non basta, aggiungi pagina
        if pdf.get_y() + total_needed > pdf.h - pdf.b_margin:
            pdf.add_page()


        pdf.set_font("DejaVu", "B", 8)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.w - 2*pdf.l_margin, LINE_HEIGHT, f"{i}. {question}")

        if image_path and os.path.exists(img_full_path):
            pdf.set_x(pdf.l_margin)
            x = pdf.get_x()
            y = pdf.get_y()
            max_width = pdf.w - 2 * pdf.l_margin
            desired_width = min(100, max_width)

            with Image.open(img_full_path) as img:
                orig_width, orig_height = img.size
            aspect_ratio = orig_height / orig_width
            desired_height = desired_width * aspect_ratio

            pdf.image(img_full_path, x=x, y=y, w=desired_width, h=desired_height)
            pdf.ln(desired_height + 5)

        correct_letter = None
        for idx, ans in enumerate(answers):
            ans_clean = clean_text(ans)
            letter = letters[idx]
            if ans == correct:
                pdf.set_text_color(0, 128, 0)
                correct_letter = letter
            else:
                pdf.set_text_color(0, 0, 0)

            pdf.set_font("DejaVu", "", 8)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.w - 2*pdf.l_margin, LINE_HEIGHT, f"{letter}. {ans_clean}")

        pdf.ln(1)

        if correct_letter:
            pdf.set_text_color(0, 128, 0)
            pdf.set_font("DejaVu", "B", 8)
            pdf.cell(0, LINE_HEIGHT, f"Answer: {correct_letter}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)

        pdf.ln(5)

    pdf.output(pdf_path)
    return pdf_path

def generate_exam_pdf_sync(responses, subject):

    file_name = "esame " + subject
    pdf_path = file_name.replace(" ", "_") + ".pdf"
    pdf = FPDF()
    pdf.add_page()
    
    # Font
    pdf.add_font('DejaVu', '', DEJAVU_TTF)
    pdf.add_font('DejaVu', 'B', os.path.join(FONTS_FOLDER, "DejaVuSans-Bold.ttf"))
    
    # Header
    pdf.set_font("DejaVu", "B", 18)
    pdf.set_text_color(0, 0, 0)
    title = f"ESAME: {subject.upper()}"
    pdf.cell(0, 12, title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)
    
    # Info riassuntiva
    correct_count = sum(1 for r in responses if r.get("point") == 1)
    total_questions = len(responses)
    percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
    
    pdf.set_font("DejaVu", "", 12)
    pdf.cell(0, 8, f"Domande corrette: {correct_count}/{total_questions} ({percentage:.1f}%)", 
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)
    
    # Linea separatrice
    pdf.set_draw_color(128, 128, 128)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(10)
    
    for i, response in enumerate(responses):
        question_text = response.get("question", "")
        user_answer = response.get("answer", "")
        is_correct = response.get("point") == 1
        
        # Calcolo spazio
        pdf.set_font("DejaVu", "B", 11)
        question_height = pdf.get_string_width(f"{i+1}. {question_text}") / (pdf.w - 2*pdf.l_margin) * 6 + 12
        
        pdf.set_font("DejaVu", "", 10)
        answer_height = pdf.get_string_width(f"Risposta: {user_answer}") / (pdf.w - 2*pdf.l_margin - 15) * 6 + 10
        
        total_height = question_height + answer_height + 25
        
        # Nuova pagina se necessario
        if pdf.get_y() + total_height > pdf.h - pdf.b_margin - 15:
            pdf.add_page()
        
        # Domanda
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(0, 0, 0)
        pdf.set_x(pdf.l_margin + 2)
        pdf.multi_cell(pdf.w - 2*pdf.l_margin - 4, 6, f"{i+1}. {question_text}")
        pdf.ln(6)
        
        # Risposta
        pdf.set_font("DejaVu", "", 8)
        pdf.set_x(pdf.l_margin + 15)
        pdf.multi_cell(pdf.w - 2*pdf.l_margin - 17, 5, f"Risposta: {user_answer}")
        pdf.ln(4)
        
        # Stato
        pdf.set_x(pdf.l_margin + 15)
        if is_correct:
            pdf.set_text_color(0, 150, 0)
            status_text = "✓ CORRETTO"
        else:
            pdf.set_text_color(200, 50, 50)
            status_text = "✗ ERRATO"
            
        pdf.set_font("DejaVu", "B", 10)
        pdf.cell(0, 6, status_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(12)  # Spazio maggiore tra le domande
        
        # Reset
        pdf.set_text_color(0, 0, 0)
    
    pdf.output(pdf_path)
    return pdf_path

async def generate_exam_pdf(responses, subject, bot, user_id):
  
    pdf_path = None
    try:
        # Chiama la versione sincrona (senza await perché non è async)
        pdf_path = generate_exam_pdf_sync(responses, subject)
        
        with open(pdf_path, "rb") as pdf_file:
            await bot.send_document(
                chat_id=user_id, 
                document=pdf_file, 
                filename=os.path.basename(pdf_path)
            )
            
    except Exception as e:
        await bot.send_message(
            chat_id=user_id, 
            text=f"❌ Errore nella generazione o invio del PDF: {e}"
        )
    finally:
        # Pulisci il file temporaneo
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)

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

