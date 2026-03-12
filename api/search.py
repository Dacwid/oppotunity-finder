"""POST /api/search — Main search endpoint."""

import json
from http.server import BaseHTTPRequestHandler
from api._utils import (
    generate_keywords, search_opportunities,
    save_search, save_results
)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}

            topic = body.get("topic", "").strip()
            level = body.get("level", "undergraduate")
            country = body.get("country", "")
            budget = body.get("budget", "Free only")
            goals = body.get("goals", "")

            if not topic:
                self._respond(400, {"error": "Topic is required"})
                return

            # Step 1: LLM generates keywords
            keywords = generate_keywords(topic, level, country, budget, goals)

            # Step 2: Web search
            results = search_opportunities(keywords)

            # Step 3: Save to CSV
            search_id = save_search(
                topic, level, country, budget, goals,
                json.dumps(keywords)
            )
            save_results(search_id, results)

            self._respond(200, {
                "search_id": search_id,
                "keywords": keywords,
                "results": results,
                "total": len(results),
            })

        except Exception as e:
            print(f"[Search Error] {e}")
            self._respond(500, {"error": str(e)})

    def do_OPTIONS(self):
        self._cors_preflight()

    def _respond(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _cors_preflight(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
