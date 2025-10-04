import re
import sqlite3
import fitz
import pytesseract
from PIL import Image

# --- Dummy database connection (for checks only, setup is in main.py) ---
DB_PATH = "dl_database.db"

# --- DL regex: 2 letters + 2 digits + optional space/hyphen + 11 digits ---
DL_REGEX = r"[A-Z]{2}\d{2}[-\s]?\d{11}"

# --- Helper function to clean common OCR misreads ---
def clean_ocr_text(text):
    text = text.upper()
    text = text.replace("O", "0")
    text = text.replace("I", "1")
    text = text.replace("|", "1")
    text = text.replace("S", "5")
    return text

# --- Method 1: Direct Text Extraction (Fast) ---
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
        return None

# --- Method 2: OCR Extraction (Slower, for Scanned PDFs) ---
def extract_text_via_ocr(pdf_path):
    """Extracts text using OCR. Slower but works for scanned PDFs."""
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                text += pytesseract.image_to_string(img)
        return text
    except Exception as e:
        print(f"Error extracting text via OCR: {e}")
        return None

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
        print("Error: Database or table not found. Please ensure DB is set up.")
        return False

# --- Main function with Hybrid Approach ---
def validate_dl_from_pdf(pdf_path):
    # Step 1: Attempt fast, direct text extraction
    print("Step 1: Attempting direct text extraction...")
    raw_text = extract_direct_text(pdf_path)

    # Step 2: If direct extraction fails or yields little text, fall back to OCR
    if not raw_text or len(raw_text.strip()) < 50:
        print("⚠️ Direct extraction failed, falling back to OCR...")
        raw_text = extract_text_via_ocr(pdf_path)
    else:
        print("✅ Text successfully extracted directly.")

    if not raw_text:
        return "Failed to extract any text from the PDF. Please check the file format or content."

    # Step 3: Clean and process the extracted text
    print("Step 2: Searching for Driving Licence numbers...")
    raw_text_clean = clean_ocr_text(raw_text)
    
    matches = re.findall(DL_REGEX, raw_text_clean)
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

# --- Entry Point for Standalone Testing ---
if __name__ == "__main__":
    # This block sets up a temporary DB for testing this script directly.
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS dl_records (id INTEGER PRIMARY KEY AUTOINCREMENT, dl_number TEXT UNIQUE)")
    cursor.execute("DELETE FROM dl_records")
    # Sample data for testing
    cursor.execute("INSERT OR IGNORE INTO dl_records (dl_number) VALUES (?)", ("CG10 20220007048",))
    cursor.execute("INSERT OR IGNORE INTO dl_records (dl_number) VALUES (?)", ("GJ15 20230009655",))
    conn.commit()
    conn.close()

    pdf_file = input("Enter path to Driving Licence PDF: ").strip().strip('"')
    print("\n--- Validation Result ---")
    print(validate_dl_from_pdf(pdf_file))
