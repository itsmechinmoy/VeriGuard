# VeriGuard

VeriGuard is a Progressive Web App (PWA) built during a hackathon to help users verify the accuracy of health-related information.  
It extracts or accepts text input, checks claims against trusted sources, and uses AI models for deeper analysis.

Currently, **image upload and OCR (text extraction from images/URLs) are not implemented** — only direct text input works.

## Live Demo

🔗 [veri-guard.vercel.app](https://veri-guard.vercel.app)

## Features

- **Input Method**: Directly type or paste health-related text.  
- **Fact-Checking**: Queries **Google Fact Check API** and **PubMed** for reliable medical information.  
- **AI Analysis**: Uses **Google Gemini** and **DeepSeek** to analyze claims and flag misinformation.  
- **PWA Support**: Installable on desktop and mobile, offline-capable for static assets.  
- **Hackathon Prototype**: Lightweight, fast, and easy to deploy.

## Usage

1. Visit [veri-guard.vercel.app](https://veri-guard.vercel.app)
2. Enter health-related text in the input box.
3. View results:
- Fact-check results from Google Fact Check API
- Scientific references from PubMed
- AI insights from Gemini and DeepSeek
4. Install as a PWA from your browser if desired.

## Notes

- OCR and image input are planned but not implemented yet.
- API keys are required for Google Fact Check, Gemini, and DeepSeek.
- Do not commit .env files with secrets.
- This is a prototype — always consult healthcare professionals for medical advice.