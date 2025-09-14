import os
import asyncio
import aiohttp
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from PIL import Image
import io
from dotenv import load_dotenv
import google.generativeai as genai
import time
import logging
import re
from difflib import SequenceMatcher

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

# Set up logging
logging.basicConfig(level=logging.INFO)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DEEPSEEK_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logging.error("Gemini API key not set during initialization")

def correct_medical_term(term):
    """Correct common typos in medical terms using similarity matching."""
    medical_terms = [
        "stomachache", "headache", "fever", "cough", "nausea", "diarrhea",
        "vomiting", "abdominal pain", "chest pain", "fatigue"
    ]
    term = term.lower().strip()
    for correct_term in medical_terms:
        similarity = SequenceMatcher(None, term, correct_term).ratio()
        if similarity > 0.8:  # Threshold for typo correction
            logging.info(f"Corrected '{term}' to '{correct_term}'")
            return correct_term
    return term

def extract_query(text):
    """Extract key medical term using Gemini, with typo correction and fallback."""
    text = text.lower().strip()
    logging.info(f"Extracting query from text: {text}")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Identify the primary health-related term or symptom in this text: '{text}'. Return only the term (e.g., 'fever', 'headache', 'stomachache'). If none, return the most relevant word or phrase."
        response = model.generate_content(prompt)
        query = response.text.strip()
        query = correct_medical_term(query)  # Correct typos
        logging.info(f"Gemini extracted query: {query}")
        return query
    except Exception as e:
        logging.error(f"Gemini query extraction error: {str(e)}")
        # Fallback: clean text and use first 1-2 words
        non_medical = ['i', 'im', 'ive', 'having', 'have', 'a', 'an', 'the', 'and', 'or', 'something']
        cleaned = re.sub(r'[^\w\s]', '', text)
        words = [w for w in cleaned.split() if w not in non_medical][:2]
        query = " ".join(words)
        query = correct_medical_term(query)  # Correct typos
        logging.info(f"Fallback query: {query}")
        return query

def perform_ai_ocr(image_file):
    """Gemini for OCR (free tier)."""
    if not GEMINI_API_KEY:
        logging.error("Gemini API key not set")
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
        logging.error(f"OCR Error: {str(e)}")
        return f"OCR Error: {str(e)}"

async def search_pubmed(query):
    """Free PubMed search via NCBI EUtils."""
    simplified_query = extract_query(query)
    logging.info(f"Searching PubMed with query: {simplified_query}")
    try:
        async with aiohttp.ClientSession() as session:
            esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {"db": "pubmed", "term": simplified_query + " causes", "retmax": 1, "retmode": "json"}
            async with session.get(esearch_url, params=params, timeout=10) as response:
                logging.info(f"PubMed esearch status: {response.status}, response: {(await response.text())[:500]}")
                response.raise_for_status()
                data = await response.json()
                ids = data.get("esearchresult", {}).get("idlist", [])
                if not ids:
                    logging.info("No PubMed results found")
                    return []
                esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                params = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
                async with session.get(esummary_url, params=params, timeout=10) as response:
                    logging.info(f"PubMed esummary status: {response.status}, response: {(await response.text())[:500]}")
                    response.raise_for_status()
                    data = await response.json()
                    results = []
                    for uid in data.get("result", {}).get("uids", []):
                        article = data["result"][uid]
                        results.append({
                            "title": article.get("title", "No title available"),
                            "authors": ", ".join([a["name"] for a in article.get("authors", [])]) or "No authors listed",
                            "pubdate": article.get("pubdate", "No date available"),
                            "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
                        })
                    logging.info(f"PubMed results: {results}")
                    return results
    except Exception as e:
        logging.error(f"PubMed error: {str(e)}, query: {simplified_query}")
        return []

async def search_fact_check(query):
    """Free Google Fact Check Tools API."""
    simplified_query = extract_query(query)
    logging.info(f"Searching fact check with query: {simplified_query}")
    if not GOOGLE_API_KEY:
        logging.error("Google API key not set")
        return []
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
            params = {"query": simplified_query, "key": GOOGLE_API_KEY, "pageSize": 3}
            async with session.get(url, params=params, timeout=10) as response:
                logging.info(f"Fact check status: {response.status}, response: {(await response.text())[:500]}")
                response.raise_for_status()
                data = await response.json()
                claims = data.get("claims", [])
                results = []
                for claim in claims:
                    for review in claim.get("claimReview", []):
                        results.append({
                            "claim": claim.get("text", "No claim text"),
                            "rating": review.get("textualRating", "No rating"),
                            "publisher": review.get("publisher", {}).get("name", "No publisher"),
                            "url": review.get("url", "No URL")
                        })
                logging.info(f"Fact check results: {results}")
                return results
    except Exception as e:
        logging.error(f"Fact check error: {str(e)}, query: {simplified_query}")
        return []

def analyze_with_gemini(text):
    """Gemini for medical analysis (free tier)."""
    if not GEMINI_API_KEY:
        logging.error("Gemini API key not set")
        return "Gemini API key not set; analysis skipped."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Analyze this medical/health advice for accuracy and reliability: {text}. Provide key facts, potential risks, and sources if known. Keep concise, under 200 words."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini analysis error: {str(e)}")
        return f"Gemini analysis unavailable: {str(e)}"

def summarize_with_deepseek(text, pubmed, fact_checks, gemini_analysis):
    """DeepSeek (via OpenRouter) using direct requests."""
    if not DEEPSEEK_API_KEY:
        logging.error("DeepSeek API key not set")
        return "DeepSeek API key not set."
    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://veriguard.onrender.com",
            "X-Title": "VeriGuard"
        }
        prompt = f"""
        Provide a concise summary of the medical advice in bullet points. Start immediately with bullet points, no introductory header. Include links to sources, flag misinformation, keep under 200 words, and avoid hallucination.
        Original text: {text}
        PubMed sources: {pubmed}
        Fact checks: {fact_checks}
        Gemini analysis: {gemini_analysis}
        """
        payload = {
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.1
        }
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"DeepSeek error: {str(e)}")
        return f"Error in summarization: {str(e)}"

def generate_chat_title(text):
    """Generate a concise chat title using Gemini."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Summarize this medical query into a short title (5-10 words) starting with 'Issues with': {text}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini title generation error: {str(e)}")
        return f"Issues with {extract_query(text)}"

@app.get("/")
async def root():
    return {"message": "VeriGuard Backend is running. Use /process for health advice analysis."}

@app.head("/")
async def head_root():
    return {"message": "VeriGuard Backend is running."}

@app.post("/process")
async def process_input(file: UploadFile = None, image_url: str = Form(None), text: str = Form(None)):
    start_time = time.time()
    logging.info("Starting /process request")
    try:
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
        logging.info(f"Text extraction took {time.time() - start_time:.2f} seconds")
        if not extracted_text:
            raise HTTPException(400, detail="No text extracted or provided")

        # Run PubMed, Fact Check, and Gemini analysis concurrently
        pubmed_start = time.time()
        fact_check_start = time.time()
        gemini_start = time.time()
        
        pubmed_task = search_pubmed(extracted_text)
        fact_check_task = search_fact_check(extracted_text)
        gemini_task = asyncio.to_thread(analyze_with_gemini, extracted_text)
        
        pubmed_results, fact_checks, gemini_analysis = await asyncio.gather(
            pubmed_task, fact_check_task, gemini_task
        )
        
        logging.info(f"PubMed search took {time.time() - pubmed_start:.2f} seconds")
        logging.info(f"Fact check took {time.time() - fact_check_start:.2f} seconds")
        logging.info(f"Gemini analysis took {time.time() - gemini_start:.2f} seconds")

        summary_start = time.time()
        summary = summarize_with_deepseek(extracted_text, pubmed_results, fact_checks, gemini_analysis)
        logging.info(f"DeepSeek summarization took {time.time() - summary_start:.2f} seconds")

        if not summary:
            summary = "No summary available due to processing error."

        chat_title = generate_chat_title(extracted_text)

        logging.info(f"Total request time: {time.time() - start_time:.2f} seconds")
        return {
            "summary": summary,
            "sources": {
                "pubmed": pubmed_results,
                "fact_checks": fact_checks
            },
            "chat_title": chat_title
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in /process: {str(e)}")
        return {
            "summary": f"Error processing request: {str(e)}",
            "sources": {
                "pubmed": [],
                "fact_checks": []
            },
            "chat_title": "Error"
        }