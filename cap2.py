# Required libraries: easyocr, PyMuPDF, Pillow, numpy
import re
import sqlite3
import fitz      # PyMuPDF
import easyocr
import numpy as np
from PIL import Image

# --- Database connection ---
DB_PATH = "dl_database.db"

# --- DL regex: 2 letters, 2 digits, optional space/hyphen, 11 digits ---
DL_REGEX = r"[A-Z]{2}\d{2}[-\s]?\d{11}"

# --- Helper function to clean common text extraction errors ---
def clean_extracted_text(text):
    """Replaces characters commonly misread during text extraction."""
    text = text.upper()
    text = text.replace("O", "0")
    text = text.replace("I", "1")
    text = text.replace("|", "1")
    text = text.replace("S", "5")
    text = text.replace("B", "8")
    return text

# --- Method 1: Direct Text Extraction (Fast) (unchanged) ---
def extract_direct_text(pdf_path):
    """Extracts text directly from a PDF. Fast but only for native PDFs."""
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        return text
    except Exception as e:
        print(f"Error during direct text extraction: {e}")
        return ""

# --- Method 2: OCR Extraction with EasyOCR (replaces Tesseract) ---
def extract_text_with_easyocr(pdf_path, dpi=300):
    """Extracts text from a scanned PDF using EasyOCR."""
    print("Initializing EasyOCR reader... (this may download models on first run)")
    reader = easyocr.Reader(['en'])
    
    full_text = []
    
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            print(f"Processing page {i + 1}/{len(doc)} with EasyOCR...")
            # Convert page to a high-resolution image (pixmap)
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_array = np.array(img)

            # Perform OCR
            result = reader.readtext(img_array)
            page_text = " ".join([text for bbox, text, prob in result])
            full_text.append(page_text)
            
        doc.close()
        return "\n".join(full_text)
    except Exception as e:
        print(f"Error during EasyOCR processing: {e}")
        return ""

# --- Normalize DL for DB comparison (unchanged) ---
def normalize_dl(dl_number):
    return re.sub(r"[-\s]", "", dl_number.upper())

# --- Check DL against DB (unchanged) ---
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
        print("Error: Database or table not found. Please ensure DB is set up.")
        return False

# --- Main function with Hybrid Approach (updated) ---
def validate_dl_from_pdf(pdf_path):
    # Step 1: Attempt fast, direct text extraction
    print("Step 1: Attempting direct text extraction...")
    raw_text = extract_direct_text(pdf_path)

    # Step 2: If direct extraction fails or yields little text, fall back to EasyOCR
    if not raw_text or len(raw_text.strip()) < 50:
        print("⚠️ Direct extraction failed or yielded little text, falling back to EasyOCR...")
        raw_text = extract_text_with_easyocr(pdf_path)
    else:
        print("✅ Text successfully extracted directly.")

    if not raw_text or not raw_text.strip():
        return "Failed to extract any text from the PDF. The file might be empty or unreadable."

    # Step 3: Clean and process the extracted text
    print("Step 3: Searching for Driving Licence numbers...")
    raw_text_clean = clean_extracted_text(raw_text)
    
    matches = list(set(re.findall(DL_REGEX, raw_text_clean))) # Use set for unique matches
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

# --- Entry Point for Standalone Testing (unchanged) ---
if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS dl_records (id INTEGER PRIMARY KEY, dl_number TEXT UNIQUE)")
    cursor.execute("DELETE FROM dl_records")
    cursor.execute("INSERT OR IGNORE INTO dl_records (dl_number) VALUES (?)", ("CG10 20220007048",))
    cursor.execute("INSERT OR IGNORE INTO dl_records (dl_number) VALUES (?)", ("GJ15 20230009655",))
    conn.commit()
    conn.close()

    try:
        pdf_file = input("Enter path to Driving Licence PDF: ").strip().strip('"')
        print("\n--- Validation Result ---")
        print(validate_dl_from_pdf(pdf_file))
    except FileNotFoundError:
        print(f"\nError: The file '{pdf_file}' was not found.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
