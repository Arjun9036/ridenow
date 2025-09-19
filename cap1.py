import re
import sqlite3
import fitz  # PyMuPDF

# ----- Database setup -----
DB_PATH = "dummy_aadhaar.db"

def create_dummy_db():
    """Sets up a simple SQLite database with a few dummy Aadhaar numbers."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS aadhaars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aadhaar TEXT NOT NULL UNIQUE
        )
    """)

    dummy_aadhaars = [
        "570453971532",
        "809471964847",
        "541309514471",
    ]

    for num in dummy_aadhaars:
        cur.execute("INSERT OR IGNORE INTO aadhaars (aadhaar) VALUES (?)", (num,))

    conn.commit()
    conn.close()
    print(f"✅ Dummy database ready at {DB_PATH}")

# ----- PDF Text Extraction -----
def extract_text_from_pdf(pdf_path):
    """
    Extracts text directly from a PDF's text layer.
    This is fast but only works for native (non-scanned) PDFs.
    """
    full_text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                full_text += page.get_text()
        return full_text
    except Exception as e:
        print(f"Error opening or reading PDF file: {e}")
        return None

# ----- Aadhaar Number Finding -----
def find_aadhaar(text):
    """Uses regex to find 12-digit numbers in the extracted text."""
    # This regex looks for 12 digits, possibly separated by spaces or hyphens.
    matches = re.findall(r'(?:\d{4}[\s-]?){2}\d{4}', text)
    clean_numbers = []
    for m in matches:
        # Remove any non-digit characters to get a clean 12-digit number.
        digits = re.sub(r'\D', '', m)
        if len(digits) == 12 and digits not in clean_numbers:
            clean_numbers.append(digits)
    return clean_numbers

# ----- Database Check -----
def check_in_db(aadhaar_number):
    """Checks if the given Aadhaar number exists in the database."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM aadhaars WHERE aadhaar = ?", (aadhaar_number,))
    result = cur.fetchone() is not None
    conn.close()
    return result

# ----- Main Validation Logic -----
def validate_aadhaar_from_pdf(pdf_path):
    """
    Main function to orchestrate the validation process.
    It extracts text, finds the number, and checks it against the database.
    """
    try:
        # Step 1: Extract text directly from the PDF.
        print("Attempting to extract text directly from PDF...")
        extracted_text = extract_text_from_pdf(pdf_path)

        if not extracted_text or not extracted_text.strip():
            return "Could not extract any text from the PDF. It might be a scanned image or empty."

        print("✅ Text successfully extracted.")

        # Step 2: Process the extracted text to find the Aadhaar number.
        aadhaars = find_aadhaar(extracted_text)
        aadhaar_number = aadhaars[0] if aadhaars else None

        if aadhaar_number:
            print(f"✅ Aadhaar Number Found: {aadhaar_number}")
            match = check_in_db(aadhaar_number)
            print(f"   Match in DB: {'✅' if match else '❌'}")
            
            if match:
                return f"Aadhaar card with number {aadhaar_number} is valid and found in the database."
            else:
                return f"Aadhaar card with number {aadhaar_number} was not found in the database."
        else:
            return "❌ No valid Aadhaar number could be found in the provided PDF."

    except Exception as e:
        return f"An unexpected error occurred during validation: {str(e)}"

# ----- Script Execution -----
if __name__ == "__main__":
    create_dummy_db()
    try:
        pdf_path = input("Enter Aadhaar PDF path: ").strip().strip('"')
        result_message = validate_aadhaar_from_pdf(pdf_path)
        print("\n--- Validation Result ---")
        print(result_message)
    except FileNotFoundError:
        print("Error: The file path you entered does not exist.")
    except Exception as e:
        print(f"A critical error occurred: {e}")
