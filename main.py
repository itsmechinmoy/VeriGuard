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
import uuid

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
        "vomiting", "abdominal pain", "chest pain", "fatigue", "sore throat",
        "back pain", "muscle pain", "joint pain", "dizziness", "constipation"
    ]
    term = term.lower().strip()
    for correct_term in medical_terms:
        similarity = SequenceMatcher(None, term, correct_term).ratio()
        if similarity > 0.8:
            logging.info(f"Corrected '{term}' to '{correct_term}'")
            return correct_term
    return term

def is_medical_query(text):
    """Check if the text is actually a medical query."""
    medical_keywords = [
        'pain', 'ache', 'hurt', 'sick', 'fever', 'cough', 'nausea', 'dizzy', 'bleeding',
        'infection', 'swelling', 'rash', 'symptom', 'disease', 'condition', 'medical',
        'doctor', 'hospital', 'medicine', 'treatment', 'cure', 'heal', 'injury',
        'broken', 'cut', 'wound', 'burn', 'bite', 'sting', 'allergy', 'asthma'
    ]
    greeting_keywords = ['hi', 'hello', 'hey', 'what are you', 'who are you', 'about', 'help']
    
    text_lower = text.lower().strip()
    
    # Check if it's a greeting or general question about the service
    if any(keyword in text_lower for keyword in greeting_keywords):
        return False
    
    # Check if it contains medical keywords
    return any(keyword in text_lower for keyword in medical_keywords)

def extract_query(text):
    """Extract key medical term using Gemini, with typo correction and fallback."""
    text = text.lower().strip()
    logging.info(f"Extracting query from text: {text}")
    
    # If not a medical query, return the original text
    if not is_medical_query(text):
        return text
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Extract the main health symptom from: '{text}'. Return only the symptom (e.g., 'fever')."
        response = model.generate_content(prompt)
        query = response.text.strip()
        query = correct_medical_term(query)
        logging.info(f"Gemini extracted query: {query}")
        return query
    except Exception as e:
        logging.error(f"Gemini query extraction error: {str(e)}")
        non_medical = ['i', 'im', 'ive', 'having', 'have', 'a', 'an', 'the', 'and', 'or', 'something', 'what', 'to', 'do', 'so', 'now']
        cleaned = re.sub(r'[^\w\s]', '', text)
        words = [w for w in cleaned.split() if w not in non_medical][:2]
        query = " ".join(words)
        query = correct_medical_term(query)
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
        prompt = "Extract health-related text from this image. Output only the text."
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
            params = {"db": "pubmed", "term": simplified_query + " treatment", "retmax": 2, "retmode": "json"}
            async with session.get(esearch_url, params=params, timeout=10) as response:
                logging.info(f"PubMed esearch status: {response.status}")
                response.raise_for_status()
                data = await response.json()
                ids = data.get("esearchresult", {}).get("idlist", [])
                if not ids:
                    logging.info("No PubMed results found")
                    return []
                esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                params = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
                async with session.get(esummary_url, params=params, timeout=10) as response:
                    logging.info(f"PubMed esummary status: {response.status}")
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
                    logging.info(f"PubMed results: {len(results)} found")
                    return results
    except Exception as e:
        logging.error(f"PubMed error: {str(e)}")
        return []

async def search_fact_check(query):
    """Free Google Fact Check Tools API - only for controversial claims."""
    # Only search for fact-checks if query contains controversial keywords
    controversial_keywords = ['cure', 'miracle', 'detox', 'cleanse', 'natural remedy', 'conspiracy']
    if not any(keyword in query.lower() for keyword in controversial_keywords):
        return []
    
    simplified_query = extract_query(query)
    logging.info(f"Searching fact check with query: {simplified_query}")
    if not GOOGLE_API_KEY:
        logging.error("Google API key not set")
        return []
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
            params = {"query": simplified_query, "key": GOOGLE_API_KEY, "pageSize": 2}
            async with session.get(url, params=params, timeout=10) as response:
                logging.info(f"Fact check status: {response.status}")
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
                logging.info(f"Fact check results: {len(results)} found")
                return results
    except Exception as e:
        logging.error(f"Fact check error: {str(e)}")
        return []

def analyze_with_gemini(text):
    """Gemini for medical analysis - focused and concise."""
    if not GEMINI_API_KEY:
        logging.error("Gemini API key not set")
        return "Analysis unavailable"
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Provide brief medical guidance for: {text}. Focus on immediate care steps and when to see a doctor. Keep under 100 words."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini analysis error: {str(e)}")
        return "Analysis unavailable"

async def summarize_with_deepseek(text, pubmed, fact_checks, gemini_analysis):
    """DeepSeek for concise medical summary or service introduction."""
    if not DEEPSEEK_API_KEY:
        logging.error("DeepSeek API key not set")
        return "Summary unavailable"
    
    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://veriguard.onrender.com",
            "X-Title": "VeriGuard"
        }
        
        # Check if this is a general inquiry about the service
        if not is_medical_query(text):
            prompt = f"""
            The user asked: {text}
            
            Respond as VeriGuard - a medical fact-checking AI assistant. Introduce yourself as:
            "I'm VeriGuard, a MediFact Checker - An AI tool for verifying health misinformation and helping with health queries. 
            
            I can help you:
            • Verify medical claims and detect misinformation
            • Provide evidence-based health guidance
            • Answer questions about symptoms and treatments
            • Find reliable medical sources
            
            Ask me about any health concern and I'll provide verified information!"
            
            Keep it friendly and under 100 words.
            """
        else:
            # Create concise prompt focused on practical medical advice
            fact_check_info = ""
            if fact_checks:
                fact_check_info = f" Note: Some claims about {extract_query(text)} may be misleading."
            
            pubmed_info = ""
            if pubmed:
                pubmed_info = f" Medical research available at: {pubmed[0]['url'] if pubmed else ''}"
            
            prompt = f"""
            User asked about: {text}

            Provide ONLY immediate practical advice in bullet points:
            - What to do right now (2-3 simple steps)
            - When to seek medical help (warning signs)
            
            Keep under 80 words. Be direct and helpful.{fact_check_info}{pubmed_info}
            
            Based on: {gemini_analysis}
            """
        
        payload = {
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150,
            "temperature": 0.1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            ) as response:
                logging.info(f"DeepSeek status: {response.status}")
                response.raise_for_status()
                data = await response.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"DeepSeek error: {str(e)}")
        # Fallback for non-medical queries
        if not is_medical_query(text):
            return "I'm VeriGuard, a MediFact Checker - An AI tool for verifying health misinformation and helping with health queries. Ask me about any health concern!"
        return f"Summary unavailable: {str(e)}"

def generate_chat_title(text):
    """Generate a natural chat title like other AI assistants."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Create a natural 2-4 word title for this query: '{text}'. Examples: 'Headache relief', 'Fever treatment', 'Back pain help'. Don't use 'Issues with'."
        response = model.generate_content(prompt)
        title = response.text.strip().strip('"').strip("'")
        logging.info(f"Generated chat title: {title}")
        return title
    except Exception as e:
        logging.error(f"Gemini title generation error: {str(e)}")
        # Fallback to natural title generation
        words = text.lower().strip().split()
        if not words:
            return "New Chat"
        
        # Common medical terms and their natural titles
        medical_mappings = {
            'headache': 'Headache relief',
            'fever': 'Fever treatment', 
            'cough': 'Cough remedy',
            'pain': 'Pain management',
            'nausea': 'Nausea help',
            'diarrhea': 'Stomach issues',
            'fatigue': 'Fatigue concerns',
            'dizzy': 'Dizziness help'
        }
        
        for word in words:
            if word in medical_mappings:
                return medical_mappings[word]
        
        # Generic fallback - take first 3 meaningful words
        meaningful_words = [w for w in words if len(w) > 2 and w not in ['the', 'and', 'but', 'for', 'are', 'with', 'can', 'you', 'have']]
        title = ' '.join(meaningful_words[:3])
        return title.capitalize() if title else "New Chat"

@app.get("/")
async def root():
    return {"message": "VeriGuard Backend is running. Use /process for health advice analysis."}

@app.head("/")
async def head_root():
    return {"message": "VeriGuard Backend is running."}

@app.post("/process")
async def process_input(file: UploadFile = None, image_url: str = Form(None), text: str = Form(None)):
    start_time = time.time()
    chat_id = str(uuid.uuid4())
    logging.info(f"Starting /process request with chat_id: {chat_id}, text: {text}")
    
    try:
        cache_key = None
        if file:
            extracted_text = perform_ai_ocr(file.file)
        elif image_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=10) as response:
                    if response.status != 200:
                        raise HTTPException(400, detail="Failed to load image from URL")
                    image = Image.open(io.BytesIO(await response.read()))
                    extracted_text = perform_ai_ocr(image)
        else:
            extracted_text = text.strip() if text else ""
            cache_key = get_cache_key(extracted_text)
            if cache_key in response_cache:
                logging.info(f"Cache hit for key: {cache_key}")
                cached = response_cache[cache_key]
                cached["chat_id"] = chat_id
                logging.info(f"Total request time: {time.time() - start_time:.2f} seconds")
                return cached

        logging.info(f"Text extraction took {time.time() - start_time:.2f} seconds")
        if not extracted_text:
            raise HTTPException(400, detail="No text extracted or provided")

        # Run async tasks concurrently
        pubmed_task = search_pubmed(extracted_text)
        fact_check_task = search_fact_check(extracted_text)
        
        # Run sync tasks in threadpool
        loop = asyncio.get_running_loop()
        gemini_task = loop.run_in_executor(None, analyze_with_gemini, extracted_text)
        title_task = loop.run_in_executor(None, generate_chat_title, extracted_text)
        
        # Wait for initial results
        results = await asyncio.gather(
            pubmed_task, fact_check_task, gemini_task, title_task,
            return_exceptions=True
        )
        
        pubmed_results = results[0] if not isinstance(results[0], Exception) else []
        fact_checks = results[1] if not isinstance(results[1], Exception) else []
        gemini_analysis = results[2] if not isinstance(results[2], Exception) else "Analysis unavailable"
        chat_title = results[3] if not isinstance(results[3], Exception) else f"Issues with {extract_query(extracted_text)}"
        
        # Generate final summary with all available data
        summary = await summarize_with_deepseek(extracted_text, pubmed_results, fact_checks, gemini_analysis)
        
        if not summary or summary == "Summary unavailable":
            # Fallback to basic Gemini response if DeepSeek fails
            summary = gemini_analysis or "Unable to provide medical guidance at this time."

        response = {
            "chat_id": chat_id,
            "summary": summary,
            "sources": {
                "pubmed": pubmed_results,
                "fact_checks": fact_checks
            },
            "chat_title": chat_title
        }

        if cache_key:
            response_cache[cache_key] = response.copy()
            logging.info(f"Cached response for key: {cache_key}")

        logging.info(f"Total request time: {time.time() - start_time:.2f} seconds")
        return response
        
    except HTTPException as he:
        logging.error(f"HTTP error in /process: {str(he)}")
        raise
    except Exception as e:
        logging.error(f"Error in /process: {str(e)}")
        return {
            "chat_id": chat_id,
            "summary": f"Sorry, I'm unable to process your request right now. Please try again later.",
            "sources": {
                "pubmed": [],
                "fact_checks": []
            },
            "chat_title": "Error Processing Request"
        }