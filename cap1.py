# Required libraries: easyocr, PyMuPDF, Pillow, numpy
import re
import sqlite3
import fitz      # PyMuPDF
import easyocr
import numpy as np
from PIL import Image

# ----- Dummy database setup (unchanged) -----
DB_PATH = "dummy_aadhaar.db"

def create_dummy_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS aadhaars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aadhaar TEXT NOT NULL UNIQUE
        )
    """)
    dummy_aadhaars = ["570453971532", "809471964847", "541309514471"]
    for num in dummy_aadhaars:
        cur.execute("INSERT OR IGNORE INTO aadhaars (aadhaar) VALUES (?)", (num,))
    conn.commit()
    conn.close()
    print(f"✅ Dummy database created at {DB_PATH}")

# ----- Method 1: Direct Text Extraction (unchanged) -----
def extract_direct_text_from_pdf(pdf_path):
    """Extracts text directly from a PDF. Fast but only works for native PDFs."""
    full_text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            full_text += page.get_text()
    return full_text

# ----- Method 2: OCR Extraction with EasyOCR (replaces Tesseract) -----
def extract_text_with_easyocr(pdf_path, dpi=300):
    """
    Extracts text from a scanned PDF using EasyOCR.
    This is slower but works for image-based documents.
    """
    print("Initializing EasyOCR reader... (this may take a moment on first run)")
    # We initialize it here so it doesn't reload the model for every page
    reader = easyocr.Reader(['en']) 
    
    full_text = []
    
    try:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            print(f"Processing page {i + 1}/{len(doc)} with EasyOCR...")
            # Convert page to a high-resolution image
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_array = np.array(img)

            # Perform OCR and extract text
            result = reader.readtext(img_array)
            page_text = " ".join([text for bbox, text, prob in result])
            full_text.append(page_text)
            
        doc.close()
        return "\n".join(full_text)
    except Exception as e:
        print(f"Error during EasyOCR processing: {e}")
        return ""

# ----- Aadhaar extraction (unchanged) -----
def find_aadhaar(text):
    matches = re.findall(r'(?:\d{4}[\s-]?){2}\d{4}', text)
    clean = []
    for m in matches:
        digits = re.sub(r'\D', '', m)
        if len(digits) == 12 and digits not in clean:
            clean.append(digits)
    return clean

# ----- Check in database (unchanged) -----
def check_in_db(aadhaar_number):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM aadhaars WHERE aadhaar = ?", (aadhaar_number,))
    result = cur.fetchone() is not None
    conn.close()
    return result

# ----- Main logic with Hybrid Approach (updated) -----
def validate_aadhaar_from_pdf(pdf_path):
    try:
        # Step 1: Try the fast, direct extraction method first.
        extracted_text = extract_direct_text_from_pdf(pdf_path)

        # Step 2: If direct extraction yields little text, fall back to EasyOCR.
        if len(extracted_text.strip()) < 50:
            print("⚠️ Direct text extraction yielded little result, falling back to EasyOCR...")
            extracted_text = extract_text_with_easyocr(pdf_path)
        else:
            print("✅ Text successfully extracted directly from PDF.")

        # Step 3: Process the extracted text to find the Aadhaar number.
        if not extracted_text:
             print("❌ OCR process failed to extract any text.")
             return "Could not extract any text from the document."

        aadhaars = find_aadhaar(extracted_text)
        aadhaar_number = aadhaars[0] if aadhaars else None

        if aadhaar_number:
            print(f"✅ Aadhaar Number Extracted: {aadhaar_number}")
            match = check_in_db(aadhaar_number)
            print(f"   Match in DB: {'✅' if match else '❌'}")
            
            if match:
                return f"Aadhaar card with number {aadhaar_number} is valid and found in the database."
            else:
                return f"Aadhaar card with number {aadhaar_number} is not found in the database."
        else:
            print("❌ Aadhaar Number not found in the extracted text.")
            return "No valid Aadhaar number could be found in the provided PDF."
    except Exception as e:
        return f"An error occurred during validation: {str(e)}"

# ----- Main execution block (unchanged) -----
if __name__ == "__main__":
    create_dummy_db()
    try:
        pdf_path = input("Enter Aadhaar PDF path: ").strip().strip('"')
        result = validate_aadhaar_from_pdf(pdf_path)
        print("\n--- Validation Result ---")
        print(result)
    except FileNotFoundError:
        print(f"Error: The file '{pdf_path}' was not found.")
    except Exception as e:
        print(f"A critical error occurred: {e}")
