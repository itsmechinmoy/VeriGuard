import os
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from PIL import Image
import io
from dotenv import load_dotenv
import google.generativeai as genai  # For Gemini OCR and analysis
from openai import OpenAI  # For DeepSeek summarization via OpenRouter

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)

def perform_ai_ocr(image_file):
    """Gemini for OCR (free tier)."""
    if not GEMINI_API_KEY:
        return "Gemini API key not set."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        if hasattr(image_file, 'read'):
            image_data = image_file.read()
            image = Image.open(io.BytesIO(image_data))
        else:
            image = image_file
        prompt = "Extract all text from this image accurately, especially health advice or handwritten notes. Output only the extracted text."
        response = model.generate_content([prompt, image])
        return response.text.strip()
    except Exception as e:
        return f"OCR Error: {str(e)}"

def search_pubmed(query):
    """Free PubMed search via NCBI EUtils."""
    try:
        esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {"db": "pubmed", "term": query, "retmax": 3, "retmode": "json"}
        response = requests.get(esearch_url, params=params, timeout=10)
        data = response.json()
        ids = data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        params = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
        response = requests.get(esummary_url, params=params, timeout=10)
        data = response.json()
        results = []
        for uid in data.get("result", {}).get("uids", []):
            article = data["result"][uid]
            results.append({
                "title": article.get("title", ""),
                "authors": ", ".join([a["name"] for a in article.get("authors", [])]),
                "pubdate": article.get("pubdate", ""),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
            })
        return results
    except:
        return []

def search_fact_check(query):
    """Free Google Fact Check Tools API."""
    if not GOOGLE_API_KEY:
        return []
    try:
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {"query": query, "key": GOOGLE_API_KEY, "pageSize": 3}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        claims = data.get("claims", [])
        results = []
        for claim in claims:
            for review in claim.get("claimReview", []):
                results.append({
                    "claim": claim.get("text", ""),
                    "rating": review.get("textualRating", ""),
                    "publisher": review.get("publisher", {}).get("name", ""),
                    "url": review.get("url", "")
                })
        return results
    except:
        return []

def analyze_with_gemini(text):
    """Gemini for medical analysis (free tier)."""
    if not GEMINI_API_KEY:
        return "Gemini API key not set."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Analyze this medical/health advice for accuracy and reliability: {text}. Provide key facts, potential risks, and sources if known. Keep concise."
        response = model.generate_content(prompt)
        return response.text
    except:
        return "Gemini analysis unavailable."

def summarize_with_deepseek(text, pubmed, fact_checks, gemini_analysis):
    """DeepSeek (via OpenRouter) to rewrite into concise response."""
    deepseek_api_key = os.getenv("OPENAI_API_KEY")
    if not deepseek_api_key:
        return "DeepSeek API key not set."
    try:
        deepseek_router_client = OpenAI(
            api_key=deepseek_api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        prompt = f"""
        Summarize the following medical advice into a short, concise response. Use bullet points, include links to sources, and flag any misinformation.
        Original text: {text}
        PubMed sources: {pubmed}
        Fact checks: {fact_checks}
        Gemini analysis: {gemini_analysis}
        Keep under 200 words, focus on key points, avoid hallucination.
        """
        response = deepseek_router_client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.1  # Low temperature to reduce hallucination
        )
        return response.choices[0].message.content.strip()
    except:
        return "Summarization unavailable."

# Add a root endpoint for health check
@app.get("/")
async def root():
    return {"message": "VeriGuard Backend is running. Use /process for health advice analysis."}

@app.post("/process")
async def process_input(file: UploadFile = None, image_url: str = Form(None), text: str = Form(None)):
    try:
        # AI OCR or text extraction
        if file:
            extracted_text = perform_ai_ocr(file.file)
        elif image_url:
            response = requests.get(image_url, stream=True, timeout=10)
            if response.status_code != 200:
                raise HTTPException(400, detail="Failed to load image from URL")
            image = Image.open(io.BytesIO(response.content))
            extracted_text = perform_ai_ocr(image)
        else:
            extracted_text = text.strip() if text else ""
        if not extracted_text:
            raise HTTPException(400, detail="No text extracted or provided")

        # Fact-checking
        pubmed_results = search_pubmed(extracted_text.replace(" ", "+"))
        fact_checks = search_fact_check(extracted_text)

        # AI analysis
        gemini_analysis = analyze_with_gemini(extracted_text)

        # Summarize
        summary = summarize_with_deepseek(extracted_text, pubmed_results, fact_checks, gemini_analysis)

        return {
            "summary": summary,
            "sources": {
                "pubmed": pubmed_results,
                "fact_checks": fact_checks
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))