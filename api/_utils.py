"""
api/_utils.py — Shared helpers for all serverless functions.

- Groq LLM client (free)
- Serper web search client (free tier)
- CSV database helpers (writes to /tmp on Vercel)
"""

import os
import csv
import json
import re
import uuid
import requests
from datetime import datetime

# ═══════════════════════════════════════════
#  CONFIG (set in Vercel Environment Variables)
# ═══════════════════════════════════════════

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# /tmp is the only writable directory on Vercel serverless
DB_DIR = "/tmp"

SEARCHES_FILE = os.path.join(DB_DIR, "searches.csv")
RESULTS_FILE = os.path.join(DB_DIR, "results.csv")
BOOKMARKS_FILE = os.path.join(DB_DIR, "bookmarks.csv")

SEARCHES_HEADERS = [
    "search_id", "timestamp", "topic", "level", "country",
    "budget", "goals", "keywords_json"
]
RESULTS_HEADERS = [
    "result_id", "search_id", "title", "url", "snippet",
    "opportunity_type", "source_domain", "found_at"
]
BOOKMARKS_HEADERS = [
    "bookmark_id", "result_id", "title", "url", "snippet",
    "opportunity_type", "bookmarked_at"
]


# ═══════════════════════════════════════════
#  GROQ LLM (free — https://console.groq.com)
# ═══════════════════════════════════════════

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
    prompt = f"""You are a keyword generator for a student opportunity search engine.

Given this student profile, generate 8-12 specific search queries to find
CV-building opportunities (workshops, free certifications, competitions, hackathons,
bootcamps, scholarships, fellowships, internships, conferences).

STUDENT PROFILE:
- Field/Interest: {topic}
- Academic Level: {level}
- Country: {country}
- Budget: {budget}
- Goals: {goals}

RULES:
1. Each keyword should be a search-engine-ready query (3-8 words)
2. Include "{country}" or "online" where relevant
3. Mix opportunity types: certifications, competitions, workshops, etc.
4. Include year "2025" or "2026" in some queries
5. Tailor to the student's level and budget
6. If budget is "Free only", focus on free/sponsored opportunities

Respond with ONLY a JSON array of strings. No explanation, no markdown.
Example: ["machine learning free certification 2025", "AI hackathon undergraduate online"]"""

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
    loc = country if country else "online"
    free = "free" if "free" in (budget or "").lower() else ""
    return [f"{topic} {t} {free} {loc} {level}".strip() for t in types]


# ═══════════════════════════════════════════
#  SERPER WEB SEARCH (free — https://serper.dev)
# ═══════════════════════════════════════════

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
            json={"q": query, "num": num_results},
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


# ═══════════════════════════════════════════
#  CSV DATABASE (/tmp on Vercel — ephemeral)
#
#  NOTE: Vercel serverless /tmp is per-invocation.
#  Data will NOT persist between cold starts.
#  This is fine for a hackathon demo.
#  For persistence, swap with Vercel KV, Supabase,
#  or any free Postgres (Neon, Railway).
# ═══════════════════════════════════════════

def _ensure_csv(filepath, headers):
    if not os.path.exists(filepath):
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(headers)


def _read_csv(filepath, headers):
    _ensure_csv(filepath, headers)
    with open(filepath, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _append_csv(filepath, headers, row):
    _ensure_csv(filepath, headers)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=headers).writerow(row)


def save_search(topic, level, country, budget, goals, keywords_json):
    sid = str(uuid.uuid4())[:8]
    _append_csv(SEARCHES_FILE, SEARCHES_HEADERS, {
        "search_id": sid,
        "timestamp": datetime.now().isoformat(),
        "topic": topic, "level": level, "country": country,
        "budget": budget, "goals": goals,
        "keywords_json": keywords_json,
    })
    return sid


def save_results(search_id, results_list):
    for r in results_list:
        _append_csv(RESULTS_FILE, RESULTS_HEADERS, {
            "result_id": str(uuid.uuid4())[:8],
            "search_id": search_id,
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("snippet", ""),
            "opportunity_type": r.get("type", "opportunity"),
            "source_domain": r.get("domain", ""),
            "found_at": datetime.now().isoformat(),
        })


def get_recent_searches(limit=20):
    rows = _read_csv(SEARCHES_FILE, SEARCHES_HEADERS)
    return rows[-limit:][::-1]


def add_bookmark(result_id, title, url, snippet, opp_type):
    bid = str(uuid.uuid4())[:8]
    _append_csv(BOOKMARKS_FILE, BOOKMARKS_HEADERS, {
        "bookmark_id": bid, "result_id": result_id,
        "title": title, "url": url, "snippet": snippet,
        "opportunity_type": opp_type,
        "bookmarked_at": datetime.now().isoformat(),
    })
    return bid


def get_bookmarks():
    return _read_csv(BOOKMARKS_FILE, BOOKMARKS_HEADERS)


def remove_bookmark(bid):
    rows = _read_csv(BOOKMARKS_FILE, BOOKMARKS_HEADERS)
    rows = [r for r in rows if r["bookmark_id"] != bid]
    with open(BOOKMARKS_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=BOOKMARKS_HEADERS)
        w.writeheader()
        w.writerows(rows)
