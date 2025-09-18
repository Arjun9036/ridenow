# main.py

import os
import sys
import sqlite3
import uvicorn
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

# Initialize the dummy database for Aadhaar validation
create_dummy_db()

# Create a FastAPI endpoint to validate Aadhaar Cards
@app.post("/validate-aadhaar")
async def validate_aadhaar_endpoint(file: UploadFile = File(...)):
    """
    Validate an Aadhaar Card from a PDF file.

    - **file**: The PDF file to be validated.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    try:
        # Save the uploaded file to a temporary location
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Call the validation function from the 'cap1.py' service file
        result = validate_aadhaar_from_pdf(temp_file_path)

        # Clean up the temporary file
        os.remove(temp_file_path)

        return JSONResponse(content={"message": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# Create a FastAPI endpoint to validate Driving Licenses
@app.post("/validate-dl")
async def validate_dl_endpoint(file: UploadFile = File(...)):
    """
    Validate a Driving Licence from a PDF file.

    - **file**: The PDF file to be validated.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    # Recreate the DL database to ensure consistency
    conn = sqlite3.connect("dl_database.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS dl_records (id INTEGER PRIMARY KEY AUTOINCREMENT, dl_number TEXT UNIQUE)")
    cursor.execute("DELETE FROM dl_records")
    cursor.execute("INSERT OR IGNORE INTO dl_records (dl_number) VALUES (?)", ("CG10 20220007048",))
    cursor.execute("INSERT OR IGNORE INTO dl_records (dl_number) VALUES (?)", ("GJ15 20230009655",))
    conn.commit()
    conn.close()

    try:
        # Save the uploaded file to a temporary location
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Call the validation function from the 'cap2.py' service file
        result = validate_dl_from_pdf(temp_file_path)

        # Clean up the temporary file
        os.remove(temp_file_path)

        return JSONResponse(content={"message": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)