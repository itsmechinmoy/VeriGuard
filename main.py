from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import io
import os
import requests
from dotenv import load_dotenv
from src.ocr_processor import extract_text_from_image
from src.fact_check_api import search_pubmed, search_fact_check
from src.grok_analysis import analyze_with_grok

# Load environment variables
load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the main HTML page
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("static/index.html", "r") as f:
        return f.read()

# Endpoint to process input (image upload, URL, or text)
@app.post("/process")
async def process_input(
    file: UploadFile = File(None),
    image_url: str = Form(None),
    text: str = Form(None)
):
    extracted_text = ""
    try:
        if file:
            # Process uploaded image
            image_data = await file.read()
            image = Image.open(io.BytesIO(image_data))
            extracted_text = extract_text_from_image(image)
        elif image_url:
            # Process image from URL
            response = requests.get(image_url, stream=True, timeout=10)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Failed to load image from URL (Status code: {response.status_code})")
            image = Image.open(io.BytesIO(response.content))
            extracted_text = extract_text_from_image(image)
        elif text:
            # Use provided text
            extracted_text = text.strip()
        else:
            raise HTTPException(status_code=400, detail="No input provided")

        if not extracted_text:
            raise HTTPException(status_code=400, detail="No text extracted or provided")

        # Save extracted text
        output_dir = "data/output"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "extracted_text.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(extracted_text)

        # PubMed search
        pubmed_query = extracted_text.replace(" ", "+")
        pubmed_results = search_pubmed(pubmed_query)

        # Google Fact Check API
        google_api_key = os.getenv("GOOGLE_API_KEY")
        fact_checks = []
        if google_api_key:
            fact_checks = search_fact_check(extracted_text, google_api_key)

        # xAI Grok API
        xai_api_key = os.getenv("XAI_API_KEY")
        grok_analysis = ""
        if xai_api_key:
            grok_analysis = analyze_with_grok(extracted_text, pubmed_results, fact_checks, xai_api_key)

        return {
            "extracted_text": extracted_text,
            "pubmed_results": pubmed_results,
            "fact_checks": fact_checks,
            "grok_analysis": grok_analysis
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")