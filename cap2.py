import re
import sqlite3
import fitz
import numpy as np
from PIL import Image

# --- Database connection ---
DB_PATH = "dl_database.db"

# --- DL regex ---
DL_REGEX = r"[A-Z]{2}\d{2}[-\s]?\d{11}"

# --- Helper function to clean text ---
def clean_extracted_text(text):
    text = text.upper().replace("O", "0").replace("I", "1").replace("|", "1").replace("S", "5").replace("B", "8")
    return text

# --- Direct Text Extraction ---
def extract_direct_text(pdf_path):
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        return text
    except Exception as e:
        print(f"Error during direct text extraction: {e}")
        return ""

# --- OCR Extraction with EasyOCR (Now accepts a pre-loaded reader) ---
def extract_text_with_easyocr(reader, pdf_path, dpi=300):
    full_text = []
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            print(f"Processing page {i + 1}/{len(doc)} with EasyOCR...")
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_array = np.array(img)
            result = reader.readtext(img_array)
            page_text = " ".join([text for bbox, text, prob in result])
            full_text.append(page_text)
        doc.close()
        return "\n".join(full_text)
    except Exception as e:
        print(f"Error during EasyOCR processing: {e}")
        return ""

# --- Normalize DL for DB comparison ---
def normalize_dl(dl_number):
    return re.sub(r"[-\s]", "", dl_number.upper())

# --- Check DL against DB ---
def check_dl_in_db(dl_number):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT dl_number FROM dl_records")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            if normalize_dl(row[0]) == normalize_dl(dl_number):
                return True
        return False
    except sqlite3.OperationalError:
        return False

# --- Main validation function (updated to accept the ocr_reader) ---
def validate_dl_from_pdf(pdf_path, ocr_reader):
    raw_text = extract_direct_text(pdf_path)

    if not raw_text or len(raw_text.strip()) < 50:
        print("⚠️ Direct extraction failed, falling back to EasyOCR...")
        # Pass the pre-loaded reader to the function
        raw_text = extract_text_with_easyocr(ocr_reader, pdf_path)
    else:
        print("✅ Text successfully extracted directly.")

    if not raw_text or not raw_text.strip():
        return "Failed to extract any text from the PDF."

    raw_text_clean = clean_extracted_text(raw_text)
    matches = list(set(re.findall(DL_REGEX, raw_text_clean)))
    matches = [m.strip() for m in matches]

    if matches:
        all_results = []
        for dl in matches:
            in_db = check_dl_in_db(dl)
            if in_db:
                all_results.append(f"✅ Driving Licence '{dl}' is valid and found in the database.")
            else:
                all_results.append(f"❌ Driving Licence '{dl}' is not in the database.")
        return "\n".join(all_results)
    else:
        return "❌ No valid Driving Licence number found in the PDF."
