# OpportunityFinder 🎯

A lot of university students have the drive to build their CV but don't know where to start looking. Opportunities like hackathons, free certifications, workshops, and scholarships exist everywhere — but they're scattered and hard to find. OpportunityFinder solves that by letting students describe their interests and goals, then using AI to search the web and surface relevant opportunities tailored to them.

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Frontend | Vanilla HTML, CSS, JavaScript |
| Backend | Python serverless functions (Vercel) |
| LLM | Groq (Llama 3.1 8B) |
| Search | Serper.dev (Google Search API) |
| Hosting | Vercel |
| Cost | $0 |

---

## Run Locally

### 1. Get free API keys

- **Groq** — https://console.groq.com
- **Serper** — https://serper.dev

### 2. Set environment variables

```bash
export GROQ_API_KEY="your-groq-key"
export SERPER_API_KEY="your-serper-key"
```

### 3. Install Vercel CLI and run

```bash
npm i -g vercel
vercel dev
```

Visit `http://localhost:3000`

---

Built for students, by a student. 🚀