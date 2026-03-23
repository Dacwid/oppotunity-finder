"""GET /api/bookmarks — list all, POST /api/bookmarks — add one."""

import json
from http.server import BaseHTTPRequestHandler
from src.api._utils import get_bookmarks, add_bookmark, remove_bookmark, get_user_id_from_token

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
            self._respond(200, get_bookmarks(token))
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def do_POST(self):
        token = _extract_token(self.headers)
        if not token:
            self._respond(401, {"error": "Login required"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            user_id = get_user_id_from_token(token)
            bid = add_bookmark(
                token=token,
                user_id=user_id,
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
        token = _extract_token(self.headers)
        if not token:
            self._respond(401, {"error": "Login required"})
            return
        try:
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            bid = qs.get("id", [""])[0]
            if bid:
                remove_bookmark(token, bid)
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _cors_preflight(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
