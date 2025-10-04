import re
import sqlite3
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# ----- Dummy database setup -----
DB_PATH = "dummy_aadhaar.db"

def create_dummy_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS aadhaars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aadhaar TEXT NOT NULL
        )
    """)

    # Fixed a missing comma in this list
    dummy_aadhaars = [
        "570453971532",
        "809471964847",
        "541309514471",
    ]

    for num in dummy_aadhaars:
        cur.execute("INSERT OR IGNORE INTO aadhaars (aadhaar) VALUES (?)", (num,))

    conn.commit()
    conn.close()
    print(f"✅ Dummy database created at {DB_PATH}")

# ----- Method 1: Direct Text Extraction (Fast) -----
def extract_direct_text_from_pdf(pdf_path):
    """Extracts text directly from a PDF. Fast but only works for native PDFs."""
    full_text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            full_text += page.get_text()
    return full_text

# ----- Method 2: OCR Extraction (Slower, for Scanned PDFs) -----
def pil_from_pix(pix):
    mode = "RGB" if pix.n >= 3 else "L"
    img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
    if mode != "RGB":
        img = img.convert("RGB")
    return img

def preprocess_basic(img):
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    img = ImageEnhance.Contrast(img).enhance(1.6)
    img = ImageEnhance.Sharpness(img).enhance(1.2)
    return img

def binarize(img, thresh=150):
    img_l = img.convert("L")
    return img_l.point(lambda p: 255 if p > thresh else 0).convert("RGB")

def extract_text_via_ocr(pdf_path, dpi=400):
    """Extracts text using OCR. Slower but works for scanned PDFs."""
    combined_pages = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img = pil_from_pix(pix)

            img_proc = preprocess_basic(img)
            texts = [
                pytesseract.image_to_string(img_proc, config="--oem 3 --psm 6"),
                pytesseract.image_to_string(img_proc, config="--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789 ")
            ]
            page_text = "\n".join(t for t in texts if t.strip())
            combined_pages.append(page_text)
    return "\n".join(combined_pages)

# ----- Aadhaar extraction -----
def find_aadhaar(text):
    matches = re.findall(r'(?:\d{4}[\s-]?){2}\d{4}', text)
    clean = []
    for m in matches:
        digits = re.sub(r'\D', '', m)
        if len(digits) == 12 and digits not in clean:
            clean.append(digits)
    return clean

# ----- Check in database -----
def check_in_db(aadhaar_number):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM aadhaars WHERE aadhaar = ?", (aadhaar_number,))
    result = cur.fetchone() is not None
    conn.close()
    return result

# ----- Main logic with Hybrid Approach -----
def validate_aadhaar_from_pdf(pdf_path):
    try:
        # Step 1: Try the fast, direct extraction method first.
        extracted_text = extract_direct_text_from_pdf(pdf_path)

        # Step 2: If direct extraction yields little text, it's likely a scanned PDF. Fall back to OCR.
        if len(extracted_text.strip()) < 50:
            print("⚠️ Direct text extraction yielded little result, falling back to OCR...")
            extracted_text = extract_text_via_ocr(pdf_path)
        else:
            print("✅ Text successfully extracted directly from PDF.")

        # Step 3: Process the extracted text to find the Aadhaar number.
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
            print("❌ Aadhaar Number not found")
            return "No valid Aadhaar number could be found in the provided PDF."
    except Exception as e:
        return f"An error occurred during validation: {str(e)}"

# This part is only for direct execution of this file
if __name__ == "__main__":
    create_dummy_db()
    pdf_path = input("Enter Aadhaar PDF path: ").strip().strip('"')
    print(validate_aadhaar_from_pdf(pdf_path))
