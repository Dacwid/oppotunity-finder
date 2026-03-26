"""
api/_utils.py — Shared helpers for all serverless functions.

- Groq LLM client (free)
- Serper web search client (free tier)
- CSV database helpers (writes to /tmp on Vercel)
"""

import os
import json
import re
import requests
import base64


#  CONFIG (set in Vercel Environment Variables)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
SUPABASE_URL      = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


#  SUPABASE CLIENT (free tier — https://supabase.com)

def get_user_id_from_token(token: str) -> str:
    try:
        payload = token.split('.')[1]
        payload += '=' * (4 - len(payload) % 4)
        data = json.loads(base64.b64decode(payload))
        return data.get('sub', '')
    except Exception:
        return ''


def _supabase(method: str, table: str, token: str, data=None, params=None):
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set.")
    headers = {
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    }
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    resp = requests.request(method, url, headers=headers, json=data, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json() if resp.text.strip() else []



#  GROQ LLM (free — https://console.groq.com)

def call_groq(prompt):
    """Call Groq free API. Returns text or None."""
    if not GROQ_API_KEY:
        return None
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1024,
            },
            timeout=25,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[Groq Error] {e}")
        return None


def generate_keywords(topic, level, country, budget, goals):
    """Use Groq to turn student profile into search keywords."""
    location = "online" if not country or country.lower() == "worldwide" else country
    prompt = f"""You are a keyword generator for a student opportunity search engine.

Given this student profile, generate 8-12 specific search queries to find
CV-building opportunities (workshops, free certifications, competitions, hackathons,
bootcamps, scholarships, fellowships, internships, conferences).

STUDENT PROFILE:
- Field/Interest: {topic}
- Academic Level: {level}
- Country: {location}
- Budget: {budget}
- Goals: {goals}

RULES:
1. Each keyword should be a search-engine-ready query (3-8 words)
2. Include "{location}" or "online" where relevant
3. Mix opportunity types: certifications, competitions, workshops, etc.
4. Include year "2026" in some queries
5. Tailor to the student's level and budget
6. If budget is "Free only", focus on free/sponsored opportunities
7. Focus on official program pages and application portals — avoid queries that would return blog posts, listicles, or "top 10" articles
8. Use specific program names or platform names (e.g. "Coursera", "Google", "AWS") when possible to target direct opportunity pages rather than blog roundups

Respond with ONLY a JSON array of strings. No explanation, no markdown.
Example: ["Google cloud certification free 2026", "AI hackathon undergraduate online"]"""

    response = call_groq(prompt)
    if response:
        try:
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except (json.JSONDecodeError, AttributeError):
            pass

    # Fallback: generate keywords locally if LLM fails
    types = ["workshop", "free certification", "competition", "hackathon",
             "bootcamp", "scholarship", "fellowship", "internship"]
    loc = location
    free = "free" if "free" in (budget or "").lower() else ""
    return [f"{topic} {t} {free} {loc} {level}".strip() for t in types]


#  SERPER WEB SEARCH (free — https://serper.dev)

def search_serper(query, num_results=8):
    """Search Google via Serper.dev free tier."""
    if not SERPER_API_KEY:
        return []
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json",
            },
            json={"q": query, "num": num_results, "gl": "us", "hl": "en"},
            timeout=12,
        )
        resp.raise_for_status()
        results = []
        for item in resp.json().get("organic", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })
        return results
    except Exception as e:
        print(f"[Serper Error] {e}")
        return []


def classify_opportunity(title, snippet):
    """Tag an opportunity by type based on keywords."""
    text = (title + " " + snippet).lower()
    types = {
        "blog": ["blog", "top 10", "top 5", "best ", "listicle", "roundup", "review"],
        "certification": ["certification", "certificate", "certified", "credential"],
        "hackathon": ["hackathon", "hack"],
        "competition": ["competition", "contest", "challenge"],
        "workshop": ["workshop", "seminar", "webinar", "training"],
        "scholarship": ["scholarship", "grant", "funding", "award"],
        "fellowship": ["fellowship", "fellow"],
        "bootcamp": ["bootcamp", "boot camp"],
        "internship": ["internship", "intern"],
        "conference": ["conference", "summit", "forum"],
        "course": ["course", "mooc", "learn", "tutorial"],
    }
    for opp_type, keywords in types.items():
        if any(kw in text for kw in keywords):
            return opp_type
    return "opportunity"


def search_opportunities(keywords):
    """Run web searches for keyword list, deduplicate, classify."""
    all_results = []
    seen_urls = set()

    for kw in keywords[:6]:
        results = search_serper(kw, num_results=5)
        for r in results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                r["type"] = classify_opportunity(r.get("title", ""), r.get("snippet", ""))
                try:
                    from urllib.parse import urlparse
                    r["domain"] = urlparse(url).hostname.replace("www.", "")
                except Exception:
                    r["domain"] = ""
                all_results.append(r)

    return all_results


# ─── SUPABASE DATABASE ────────────────────────────────────────────────────────

def save_search(token, user_id, topic, level, country, budget, goals, keywords):
    kw_list = keywords if isinstance(keywords, list) else json.loads(keywords)
    result = _supabase('POST', 'searches', token, {
        'user_id': user_id, 'topic': topic, 'level': level,
        'country': country, 'budget': budget, 'goals': goals,
        'keywords': kw_list,
    })
    return result[0]['id'] if result else None


def save_results(token, user_id, search_id, results_list):
    for r in results_list:
        _supabase('POST', 'results', token, {
            'user_id': user_id, 'search_id': search_id,
            'title': r.get('title', ''), 'url': r.get('url', ''),
            'snippet': r.get('snippet', ''),
            'opportunity_type': r.get('type', 'opportunity'),
            'source_domain': r.get('domain', ''),
        })


def get_recent_searches(token, limit=20):
    return _supabase('GET', 'searches', token, params={
        'order': 'created_at.desc', 'limit': str(limit),
        'select': 'id,topic,level,country,budget,goals,keywords,created_at',
    })


def add_bookmark(token, user_id, result_id, title, url, snippet, opp_type):
    result = _supabase('POST', 'bookmarks', token, {
        'user_id': user_id, 'result_id': result_id or None,
        'title': title, 'url': url, 'snippet': snippet,
        'opportunity_type': opp_type,
    })
    return result[0]['id'] if result else None


def get_bookmarks(token):
    return _supabase('GET', 'bookmarks', token, params={
        'order': 'created_at.desc',
        'select': 'id,title,url,snippet,opportunity_type,created_at',
    })


def remove_bookmark(token, bid):
    _supabase('DELETE', 'bookmarks', token, params={'id': f'eq.{bid}'})