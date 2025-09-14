import os
import asyncio
import aiohttp
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
from dotenv import load_dotenv
import google.generativeai as genai
import time
import logging
import re
from difflib import SequenceMatcher
from functools import lru_cache
import hashlib

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

# In-memory cache
response_cache = {}

def get_cache_key(text):
    """Generate a cache key from input text."""
    return hashlib.md5(text.lower().strip().encode()).hexdigest()

@lru_cache(maxsize=100)
def correct_medical_term(term):
    """Correct common typos in medical terms using similarity matching."""
    medical_terms = [
        "stomachache", "headache", "fever", "cough", "nausea", "diarrhea",
        "vomiting", "abdominal pain", "chest pain", "fatigue"
    ]
    term = term.lower().strip()
    for correct_term in medical_terms:
        similarity = SequenceMatcher(None, term, correct_term).ratio()
        if similarity > 0.8:
            logging.info(f"Corrected '{term}' to '{correct_term}'")
            return correct_term
    return term

async def extract_query(text):
    """Extract key medical term using Gemini, with typo correction and fallback."""
    text = text.lower().strip()
    logging.info(f"Extracting query from text: {text}")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Identify the primary health-related term or symptom in this text: '{text}'. Return only the term (e.g., 'fever', 'headache', 'stomachache'). If none, return the most relevant word or phrase."
        response = await model.generate_content_async(prompt)
        query = response.text.strip()
        query = correct_medical_term(query)
        logging.info(f"Gemini extracted query: {query}")
        return query
    except Exception as e:
        logging.error(f"Gemini query extraction error: {str(e)}")
        non_medical = ['i', 'im', 'ive', 'having', 'have', 'a', 'an', 'the', 'and', 'or', 'something', 'what', 'to', 'do']
        cleaned = re.sub(r'[^\w\s]', '', text)
        words = [w for w in cleaned.split() if w not in non_medical][:2]
        query = " ".join(words)
        query = correct_medical_term(query)
        logging.info(f"Fallback query: {query}")
        return query

async def perform_ai_ocr(image_file):
    """Gemini for OCR (free tier)."""
    if not GEMINI_API_KEY:
        logging.error("Gemini API key not set")
        return "Gemini API key not set."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        if hasattr(image_file, 'read'):
            image_data = await image_file.read()
            image = Image.open(io.BytesIO(image_data))
        else:
            image = image_file
        prompt = "Extract all text from this image accurately, especially health advice or handwritten notes. Output only the extracted text."
        response = await model.generate_content_async([prompt, image])
        return response.text.strip()
    except Exception as e:
        logging.error(f"OCR Error: {str(e)}")
        return f"OCR Error: {str(e)}"

async def search_pubmed(query):
    """Free PubMed search via NCBI EUtils."""
    simplified_query = await extract_query(query)
    logging.info(f"Searching PubMed with query: {simplified_query}")
    try:
        async with aiohttp.ClientSession() as session:
            esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {"db": "pubmed", "term": simplified_query + " causes", "retmax": 1, "retmode": "json"}
            async with session.get(esearch_url, params=params, timeout=5) as response:
                logging.info(f"PubMed esearch status: {response.status}, response: {(await response.text())[:500]}")
                response.raise_for_status()
                data = await response.json()
                ids = data.get("esearchresult", {}).get("idlist", [])
                if not ids:
                    logging.info("No PubMed results found")
                    return []
                esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                params = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
                async with session.get(esummary_url, params=params, timeout=5) as response:
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
    simplified_query = await extract_query(query)
    logging.info(f"Searching fact check with query: {simplified_query}")
    if not GOOGLE_API_KEY:
        logging.error("Google API key not set")
        return []
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
            params = {"query": simplified_query, "key": GOOGLE_API_KEY, "pageSize": 3}
            async with session.get(url, params=params, timeout=5) as response:
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

async def analyze_with_gemini(text):
    """Gemini for medical analysis (free tier)."""
    if not GEMINI_API_KEY:
        logging.error("Gemini API key not set")
        return "Gemini API key not set; analysis skipped."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Analyze this medical/health advice for accuracy and reliability: {text}. Provide key facts, potential risks, and sources if known. Keep concise, under 100 words."
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini analysis error: {str(e)}")
        return f"Gemini analysis unavailable: {str(e)}"

async def summarize_with_deepseek(text, pubmed, fact_checks, gemini_analysis):
    """DeepSeek (via OpenRouter) using async requests."""
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
        Summarize this medical advice in concise bullet points (no header). Include source links, flag misinformation, keep under 100 words.
        Text: {text}
        PubMed: {pubmed}
        Fact checks: {fact_checks}
        Analysis: {gemini_analysis}
        """
        payload = {
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.1
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=5
            ) as response:
                logging.info(f"DeepSeek status: {response.status}, response: {(await response.text())[:500]}")
                response.raise_for_status()
                data = await response.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"DeepSeek error: {str(e)}")
        return f"Error in summarization: {str(e)}"

async def generate_chat_title(text):
    """Generate a concise chat title using Gemini."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Summarize this medical query into a short title (5-10 words) starting with 'Issues with': {text}"
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini title generation error: {str(e)}")
        return f"Issues with {await extract_query(text)}"

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
        cache_key = None
        if file:
            extracted_text = await perform_ai_ocr(file)
        elif image_url:
            async with aiohttp.ClientSession() as session:
                response = await session.get(image_url, timeout=5)
                if response.status != 200:
                    raise HTTPException(400, detail="Failed to load image from URL")
                image = Image.open(io.BytesIO(await response.read()))
                extracted_text = await perform_ai_ocr(image)
        else:
            extracted_text = text.strip() if text else ""
            cache_key = get_cache_key(extracted_text)
            if cache_key in response_cache:
                logging.info(f"Cache hit for key: {cache_key}")
                cached = response_cache[cache_key]
                logging.info(f"Total request time: {time.time() - start_time:.2f} seconds")
                return cached

        logging.info(f"Text extraction took {time.time() - start_time:.2f} seconds")
        if not extracted_text:
            raise HTTPException(400, detail="No text extracted or provided")

        pubmed_start = time.time()
        fact_check_start = time.time()
        gemini_start = time.time()
        title_start = time.time()
        summary_start = time.time()
        
        pubmed_task = search_pubmed(extracted_text)
        fact_check_task = search_fact_check(extracted_text)
        gemini_task = analyze_with_gemini(extracted_text)
        title_task = generate_chat_title(extracted_text)
        summary_task = summarize_with_deepseek(extracted_text, [], [], "Pending analysis...")  # Start early with placeholders
        
        results = await asyncio.gather(
            pubmed_task, fact_check_task, gemini_task, title_task, summary_task,
            return_exceptions=True
        )
        
        pubmed_results = results[0] if not isinstance(results[0], Exception) else []
        fact_checks = results[1] if not isinstance(results[1], Exception) else []
        gemini_analysis = results[2] if not isinstance(results[2], Exception) else "Analysis unavailable"
        chat_title = results[3] if not isinstance(results[3], Exception) else f"Issues with {await extract_query(extracted_text)}"
        summary_prelim = results[4] if not isinstance(results[4], Exception) else "Summary unavailable"
        
        # Update summary with actual results
        if pubmed_results or fact_checks or gemini_analysis != "Pending analysis...":
            summary = await summarize_with_deepseek(extracted_text, pubmed_results, fact_checks, gemini_analysis)
        else:
            summary = summary_prelim

        logging.info(f"PubMed search took {time.time() - pubmed_start:.2f} seconds")
        logging.info(f"Fact check took {time.time() - fact_check_start:.2f} seconds")
        logging.info(f"Gemini analysis took {time.time() - gemini_start:.2f} seconds")
        logging.info(f"Title generation took {time.time() - title_start:.2f} seconds")
        logging.info(f"DeepSeek summarization took {time.time() - summary_start:.2f} seconds")

        if not summary:
            summary = "No summary available due to processing error."

        response = {
            "summary": summary,
            "sources": {
                "pubmed": pubmed_results,
                "fact_checks": fact_checks
            },
            "chat_title": chat_title
        }

        if cache_key:
            response_cache[cache_key] = response
            logging.info(f"Cached response for key: {cache_key}")

        logging.info(f"Total request time: {time.time() - start_time:.2f} seconds")
        return response
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