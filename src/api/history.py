"""GET /api/history — Recent search history."""

import json
from http.server import BaseHTTPRequestHandler
from src.api._utils import get_recent_searches

def _extract_token(headers):
    auth = headers.get("Authorization", "")
    return auth[7:] if auth.startswith("Bearer ") else None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        token = _extract_token(self.headers)
        if not token:
            self._respond(401, {"error": "Login required"})
            return
        try:
            self._respond(200, get_recent_searches(token, 20))
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def do_OPTIONS(self):
        self._cors_preflight()

    def _respond(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _cors_preflight(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
