import os
import sys
import sqlite3
import uvicorn
import easyocr
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import shutil

# Add the 'services' directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "services"))

# Import validation functions from the services module
from cap1 import validate_aadhaar_from_pdf, create_dummy_db
from cap2 import validate_dl_from_pdf

app = FastAPI(
    title="Document Validation API",
    description="An API to validate Aadhaar Cards and Driving Licences from PDF files.",
    version="1.0.0"
)

# This will hold our single, pre-loaded EasyOCR reader instance
ocr_reader = None

@app.on_event("startup")
async def startup_event():
    """
    This function runs when the FastAPI application starts.
    It pre-loads the EasyOCR models to avoid timeouts on the first request.
    """
    global ocr_reader
    print("Application startup: Loading EasyOCR models...")
    # Initialize the reader and store it in the global variable
    ocr_reader = easyocr.Reader(['en'])
    print("✅ EasyOCR models loaded successfully. Application is ready.")

# Initialize the dummy database for Aadhaar validation
create_dummy_db()

@app.post("/validate-aadhaar")
async def validate_aadhaar_endpoint(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    temp_file_path = f"temp_{file.filename}"
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Pass the pre-loaded ocr_reader to the validation function
        result = validate_aadhaar_from_pdf(temp_file_path, ocr_reader)

        return JSONResponse(content={"message": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.post("/validate-dl")
async def validate_dl_endpoint(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    # Setup the DL database for the request
    conn = sqlite3.connect("dl_database.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS dl_records (id INTEGER PRIMARY KEY, dl_number TEXT UNIQUE)")
    cursor.execute("DELETE FROM dl_records")
    cursor.execute("INSERT OR IGNORE INTO dl_records (dl_number) VALUES (?)", ("CG10 20220007048",))
    cursor.execute("INSERT OR IGNORE INTO dl_records (dl_number) VALUES (?)", ("GJ15 20230009655",))
    conn.commit()
    conn.close()

    temp_file_path = f"temp_{file.filename}"
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Pass the pre-loaded ocr_reader to the validation function
        result = validate_dl_from_pdf(temp_file_path, ocr_reader)

        return JSONResponse(content={"message": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
