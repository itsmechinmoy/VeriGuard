# VeriGuard

VeriGuard is a Progressive Web App (PWA) designed for a hackathon to scan health advice from images (via upload or URL) or typed text, extract text using OCR, and verify accuracy using PubMed, Google Fact Check, and xAI Grok APIs. Built with FastAPI (backend) and HTML/JavaScript/Tailwind CSS (frontend).

## Live Demo

Access the app at [veriguard-hackathon.netlify.app](https://veriguard-hackathon.netlify.app).

## Features

- **Input Methods**: Upload images, provide image URLs, or type health advice.
- **OCR**: Extracts text from images using Tesseract.
- **Fact-Checking**: Searches PubMed for articles and Google Fact Check for claims.
- **AI Analysis**: Uses xAI Grok API to analyze and flag misinformation.
- **PWA**: Installable, works offline (static files), and mobile-friendly.
- **Dynamic Storage**: Saves extracted text to `data/output/extracted_text.txt` (on backend server).

## Setup (Local Development)

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
   - Linux: `sudo apt install tesseract-ocr libtesseract-dev`
   - macOS: `brew install tesseract`
   - Add Tesseract to system PATH or specify in `src/ocr_processor.py` (e.g., `pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'`).

4. **Set Up Environment Variables**:

   - Create a `.env` file in the root:
     ```plaintext
     GOOGLE_API_KEY=your_google_fact_check_api_key
     XAI_API_KEY=your_xai_grok_api_key
     ```
   - Get keys from [Google Developer Console](https://console.developers.google.com/) and [xAI API](https://x.ai/api).

5. **Run the Backend**:
   ```bash
   uvicorn main:app --reload
   ```
   - Access at `http://localhost:8000` (frontend and backend locally).

## Usage

1. Visit [veriguard-hackathon.netlify.app](https://veriguard-hackathon.netlify.app).
2. Choose an input method:
   - **Upload Image**: Select a jpg/png/jpeg file.
   - **Image URL**: Enter a direct URL (e.g., `https://example.com/note.jpg`).
   - **Type Text**: Enter health advice text.
3. Enter API keys (optional) if not set in backend environment.
4. View results: extracted text, PubMed articles, fact-checks, and Grok AI analysis.
5. Install as a PWA via the browser’s install prompt.

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
│   └── output/         # Dynamic storage for extracted text (backend)
├── src/
│   ├── ocr_processor.py  # OCR logic
│   ├── fact_check_api.py # Fact-checking API logic
│   └── grok_analysis.py  # Grok AI analysis logic
└── docs/
    └── setup_guide.md  # Detailed setup instructions
```

## Deployment

- **Frontend**: Hosted on Netlify at [veriguard-hackathon.netlify.app](https://veriguard-hackathon.netlify.app).
  - **Base directory**: `static`
  - **Build command**: Blank or `echo "No build required"`
  - **Publish directory**: `static`
- **Backend**: Requires separate hosting (e.g., Render, Heroku) for FastAPI. Update `static/script.js` with the backend URL (e.g., `https://veriguard-backend.onrender.com/process`).

## Notes

- Prototype for hackathon; consult healthcare professionals for medical advice.
- Secure API keys in `.env` or via UI input; do not commit to Git.
- PWA caches static files for offline use; API calls require internet.
- Replace placeholder icons in `manifest.json` with custom 192x192 and 512x512 PNGs.
- License: MIT
