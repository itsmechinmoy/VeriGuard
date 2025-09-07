# VeriGuard PWA

VeriGuard is a Progressive Web App (PWA) that scans health advice from images (via upload or URL) or typed text, extracts text using OCR, and verifies accuracy using PubMed, Google Fact Check, and xAI Grok APIs. Built with FastAPI (backend) and HTML/JavaScript/Tailwind CSS (frontend).

## Features
- **Input Methods**: Upload images, provide image URLs, or type health advice.
- **OCR**: Extracts text from images using Tesseract.
- **Fact-Checking**: Searches PubMed for articles and Google Fact Check for claims.
- **AI Analysis**: Uses xAI Grok API to analyze and flag misinformation.
- **PWA**: Installable, works offline (basic caching), and mobile-friendly.
- **Dynamic Storage**: Saves extracted text to `data/output/extracted_text.txt`.

## Setup
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/itsmechinmoy/VeriGuard.git
   cd VeriGuard
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Tesseract**:
   - Windows: Download from [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
   - Linux/macOS: Install via package manager (e.g., `sudo apt install tesseract-ocr` or `brew install tesseract`).
   - Add Tesseract to system PATH or specify in `main.py` if needed.

4. **Set Up Environment Variables**:
   - Create a `.env` file:
     ```plaintext
     GOOGLE_API_KEY=your_google_fact_check_api_key
     XAI_API_KEY=your_xai_grok_api_key
     ```
   - Get Google API key from [Google Developer Console](https://console.developers.google.com/).
   - Get xAI API key from [xAI API](https://x.ai/api).

5. **Run the App**:
   ```bash
   uvicorn main:app --reload
   ```
   - Access at `http://localhost:8000`.

## Usage
1. Open the app in a browser (`http://localhost:8000`).
2. Choose an input method:
   - **Upload Image**: Select a jpg/png/jpeg file.
   - **Image URL**: Enter a direct URL (e.g., `https://example.com/note.jpg`).
   - **Type Text**: Enter health advice text.
3. Enter API keys if not set in `.env`.
4. View results (extracted text, PubMed articles, fact-checks, Grok analysis).
5. Install as a PWA by clicking the browser's install prompt.

## Project Structure
```
VeriGuard/
├── main.py             # FastAPI backend
├── requirements.txt    # Python dependencies
├── README.md           # Project documentation
├── .gitignore          # Git ignore file
├── static/             # Frontend files
│   ├── index.html      # Main HTML page
│   ├── script.js       # JavaScript logic
│   ├── manifest.json   # PWA manifest
│   └── service-worker.js # PWA service worker
├── data/
│   └── output/         # Dynamic storage for extracted text
├── src/
│   ├── ocr_processor.py  # OCR logic
│   ├── fact_check_api.py # Fact-checking API logic
│   └── grok_analysis.py  # Grok AI analysis logic
└── docs/
    └── setup_guide.md  # Detailed setup instructions
```

## Notes
- Prototype for demonstration; consult healthcare professionals for advice.
- Secure API keys and avoid committing them to Git.
- PWA offline mode caches static files; API calls require internet.
- License: MIT