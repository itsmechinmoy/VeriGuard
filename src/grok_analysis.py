import requests
import json

def analyze_with_grok(text, pubmed_results, fact_checks, api_key):
    endpoint = "https://api.grok.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    prompt = f"Analyze this health advice for accuracy and flag any misinformation: '{text}'.\n"
    if pubmed_results:
        prompt += "Related PubMed articles:\n" + "\n".join([f"- {r['title']}" for r in pubmed_results]) + "\n"
    if fact_checks:
        prompt += "Fact checks:\n" + "\n".join([f"- Rating: {review.get('textualRating', 'N/A')} for claim '{claim.get('text', '')}'" for claim in fact_checks for review in claim.get("claimReview", [])]) + "\n"
    prompt += "Provide corrections and explanations based on reliable sources like WHO or PubMed."

    try:
        body = {
            "model": "grok-beta",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": 0.7
        }
        response = requests.post(endpoint, headers=headers, json=body, timeout=10)
        if response.status_code != 200:
            return f"Error: Grok API returned status {response.status_code}"
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "No response.")
    except Exception:
        return "Error in API call."