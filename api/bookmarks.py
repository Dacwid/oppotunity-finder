"""GET /api/bookmarks — list all, POST /api/bookmarks — add one."""

import json
from http.server import BaseHTTPRequestHandler
from api._utils import get_bookmarks, add_bookmark, remove_bookmark


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self._respond(200, get_bookmarks())
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}

            bid = add_bookmark(
                result_id=body.get("result_id", ""),
                title=body.get("title", ""),
                url=body.get("url", ""),
                snippet=body.get("snippet", ""),
                opp_type=body.get("type", "opportunity"),
            )
            self._respond(200, {"bookmark_id": bid})

        except Exception as e:
            self._respond(500, {"error": str(e)})

    def do_DELETE(self):
        try:
            # Extract bookmark_id from query string
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            bid = qs.get("id", [""])[0]
            if bid:
                remove_bookmark(bid)
            self._respond(200, {"status": "removed"})
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def do_OPTIONS(self):
        self._cors_preflight()

    def _respond(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _cors_preflight(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
