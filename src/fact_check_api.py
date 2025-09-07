import requests

def search_pubmed(query, num_results=5):
    esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    esearch_params = {
        "db": "pubmed",
        "term": query,
        "retmax": num_results,
        "retmode": "json"
    }
    try:
        esearch_response = requests.get(esearch_url, params=esearch_params, timeout=10)
        if esearch_response.status_code != 200:
            return []
        esearch_data = esearch_response.json()
        ids = esearch_data.get("esearchresult", {}).get("idlist", [])

        if not ids:
            return []

        esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        esummary_params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "json"
        }
        esummary_response = requests.get(esummary_url, params=esummary_params, timeout=10)
        if esummary_response.status_code != 200:
            return []
        esummary_data = esummary_response.json()
        results = []
        for uid in esummary_data.get("result", {}).get("uids", []):
            article = esummary_data["result"][uid]
            title = article.get("title", "No title")
            authors = ", ".join([author["name"] for author in article.get("authors", [])])
            pubdate = article.get("pubdate", "Unknown date")
            results.append({
                "title": title,
                "authors": authors,
                "pubdate": pubdate
            })
        return results
    except Exception:
        return []

def search_fact_check(query, api_key):
    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    params = {
        "query": query,
        "key": api_key,
        "pageSize": 5
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return []
        data = response.json()
        return data.get("claims", [])
    except Exception:
        return []