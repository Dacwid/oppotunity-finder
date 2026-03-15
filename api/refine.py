"""POST /api/refine — Re-search with user-edited keywords."""

import json
from http.server import BaseHTTPRequestHandler
from api._utils import search_opportunities, save_search, save_results


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}

            keywords = body.get("keywords", [])
            if not keywords:
                self._respond(400, {"error": "Keywords are required"})
                return

            results = search_opportunities(keywords)

            search_id = save_search(
                "(refined search)", "", "", "", "",
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
