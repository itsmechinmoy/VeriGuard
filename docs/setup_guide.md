# Setup Guide for VeriGuard PWA

This guide provides instructions to set up and run the VeriGuard Progressive Web App (PWA).

## Prerequisites
- **Python 3.8+**: Install from [python.org](https://www.python.org/downloads/).
- **Tesseract OCR**: Required for text extraction.
  - **Windows**: Download from [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
  - **Linux**: `sudo apt install tesseract-ocr libtesseract-dev`
  - **macOS**: `brew install tesseract`
  - Ensure Tesseract is in system PATH or specify in `main.py` if needed.
- **Git**: For cloning the repository.
- **API Keys** (optional):
  - Google Fact Check API: [Google Developer Console](https://console.developers.google.com/).
  - xAI Grok API: [xAI API](https://x.ai/api).

## Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/itsmechinmoy/VeriGuard.git
   cd VeriGuard
   ```

2. **Create Virtual Environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**:
   - Create a `.env` file:
     ```plaintext
     GOOGLE_API_KEY=your_google_fact_check_api_key
     XAI_API_KEY=your_xai_grok_api_key
     ```

5. **Run the App**:
   ```bash
   uvicorn main:app --reload
   ```
   - Access at `http://localhost:8000`.

## Troubleshooting
- **Tesseract Not Found**: Verify Tesseract installation with `tesseract --version`.
- **API Errors**: Check API keys and quotas. See [Google Fact Check API](https://developers.google.com/fact-check/tools/api) or [xAI API](https://x.ai/api).
- **Image Loading**: Use direct image URLs (jpg/png/jpeg).
- **PWA Issues**: Ensure HTTPS for production or use `localhost` for testing.

## Notes
- The app dynamically creates `data/output/` for extracted text.
- PWA caches static files for offline use; API calls require internet.
- Consult healthcare professionals for medical advice.