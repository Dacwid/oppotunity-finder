# OpportunityFinder 🎯

> **Hackathon Project** — AI-powered opportunity search engine for undergrad students to build their CV.

Students describe their interests, academic level, country, budget, and goals. AI generates targeted search keywords, then web-crawls for workshops, free certifications, competitions, hackathons, scholarships & more.

**Live on Vercel. Total cost: $0.**

---

## Architecture

```
opportunity-finder/
├── public/                  ← Static frontend (HTML/CSS/JS)
│   ├── index.html           ← Intake form + results pages
│   ├── styles.css           ← Styling
│   └── app.js               ← Client logic
├── api/                     ← Vercel Serverless Functions (Python)
│   ├── _utils.py            ← Shared: Groq LLM + Serper search + CSV DB
│   ├── search.py            ← POST /api/search
│   ├── refine.py            ← POST /api/refine
│   ├── bookmarks.py         ← GET/POST/DELETE /api/bookmarks
│   └── history.py           ← GET /api/history
├── vercel.json              ← Routing config
├── requirements.txt         ← Python deps
└── README.md
```

---

## Deploy to Vercel (5 minutes)

### 1. Get free API keys

| Service | Free tier | Sign up |
|---------|-----------|---------|
| **Groq** | Free, generous limits | https://console.groq.com |
| **Serper** | 2,500 searches/month free | https://serper.dev |

### 2. Deploy

```bash
# Install Vercel CLI
npm i -g vercel

# Clone/download this project, then:
cd opportunity-finder
vercel
```

### 3. Set environment variables

In the Vercel dashboard → your project → Settings → Environment Variables:

```
GROQ_API_KEY    = gsk_xxxxxxxxxxxx
SERPER_API_KEY  = xxxxxxxxxxxxxxxx
```

Or via CLI:
```bash
vercel env add GROQ_API_KEY
vercel env add SERPER_API_KEY
```

### 4. Redeploy

```bash
vercel --prod
```

That's it! Your app is live at `https://your-project.vercel.app`

---

## Run Locally

```bash
# Install Vercel CLI
npm i -g vercel

# Set env vars
export GROQ_API_KEY="your-key"
export SERPER_API_KEY="your-key"

# Run local dev server (emulates Vercel serverless)
vercel dev
```

Visit `http://localhost:3000`

---

## How It Works

```
┌─────────────────────┐
│  Student fills form  │  topic, description, level, country, budget, format, types
└──────────┬──────────┘
           │ POST /api/search
           ▼
┌─────────────────────┐
│  Groq LLM (free)    │  Generates 8-12 targeted search keywords
│  llama-3.1-8b       │  from student profile
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Serper.dev (free)   │  Searches Google for each keyword
│  Web Search API      │  Returns titles, URLs, snippets
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Classifier          │  Tags results: certification, hackathon,
│  (keyword-based)     │  competition, workshop, scholarship, etc.
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Results Page        │  Search-engine style cards
│  + Edit Keywords     │  Filter by type, bookmark, re-search
└─────────────────────┘
```

---

## Intake Form Fields

The form collects rich context so the AI generates better keywords:

| Field | Purpose |
|-------|---------|
| **Topic** | Main field of interest |
| **Description** | Free-text details about what they want |
| **Academic Level** | Freshman → Master's (affects keyword relevance) |
| **Country** | Location-specific opportunities |
| **Budget** | Free only / Under $50 / Under $200 / Any |
| **Format** | Online / In-person / Hybrid |
| **Opportunity Types** | Checkboxes: certifications, competitions, hackathons, workshops, scholarships, fellowships, internships, conferences |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/search` | Main search — profile → keywords → results |
| POST | `/api/refine` | Re-search with edited keywords |
| GET | `/api/bookmarks` | List saved bookmarks |
| POST | `/api/bookmarks` | Save a bookmark |
| DELETE | `/api/bookmarks?id=xxx` | Remove a bookmark |
| GET | `/api/history` | Recent search history |

---

## Note on Data Persistence

Vercel serverless functions use `/tmp` which is **ephemeral** — data resets on cold starts. This is fine for a hackathon demo. For production persistence, swap CSV storage in `_utils.py` with:

- **Vercel KV** (free tier) — Redis-like key-value store
- **Supabase** (free tier) — Postgres database
- **Neon** (free tier) — Serverless Postgres
- **Upstash** (free tier) — Redis

---

## Tech Stack

- **Frontend:** Vanilla HTML + CSS + JS (no build, no framework)
- **Backend:** Python serverless functions on Vercel
- **LLM:** Groq (free) running Llama 3.1 8B
- **Search:** Serper.dev (free tier, 2,500/month)
- **Storage:** CSV in /tmp (ephemeral) or swap with any free DB

**Total cost: $0**

---

MIT License — Built for hackathons 🚀
