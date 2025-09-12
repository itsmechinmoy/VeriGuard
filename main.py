import os
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.ocr_processor import extract_text_from_image
from src.fact_check_api import get_fact_checks
from src.grok_analysis import analyze_with_grok
import openai
import requests
from PIL import Image
import io

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production (e.g., "https://veriguard-hackathon.netlify.app")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load API keys from environment variables (GitHub Secrets)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
openai.api_key = OPENAI_API_KEY

@app.post("/process")
async def process_input(file: UploadFile = None, image_url: str = Form(None), text: str = Form(None)):
    extracted_text = ""
    try:
        if file:
            extracted_text = extract_text_from_image(file.file)
        elif image_url:
            response = requests.get(image_url, stream=True, timeout=10)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Failed to load image from URL (Status code: {response.status_code})")
            image = Image.open(io.BytesIO(response.content))
            extracted_text = extract_text_from_image(image)
        elif text:
            extracted_text = text.strip()
        else:
            raise HTTPException(status_code=400, detail="No input provided")

        if not extracted_text:
            raise HTTPException(status_code=400, detail="No text extracted or provided")

        # Fact-checking with Google
        fact_checks = get_fact_checks(extracted_text, GOOGLE_API_KEY) if GOOGLE_API_KEY else []

        # Grok analysis
        grok_analysis = analyze_with_grok(extracted_text, XAI_API_KEY) if XAI_API_KEY else "Grok API key not set"

        # ChatGPT analysis
        chatgpt_analysis = "ChatGPT API key not set"
        if OPENAI_API_KEY:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # or "gpt-4" if available
                messages=[{"role": "user", "content": f"Analyze this health advice for accuracy: {extracted_text}"}],
                max_tokens=150
            )
            chatgpt_analysis = response.choices[0].message['content'].strip()

        # PubMed search (placeholder)
        pubmed_results = []  # Implement PubMed API integration here

        return {
            "extracted_text": extracted_text,
            "pubmed_results": pubmed_results,
            "fact_checks": fact_checks,
            "grok_analysis": grok_analysis,
            "chatgpt_analysis": chatgpt_analysis
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)