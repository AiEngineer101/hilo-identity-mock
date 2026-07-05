#!/usr/bin/env python3
"""Hilo identity-lookup mock backend for Intercom soft-identity testing.
GET /?email=x        -> {"found": true, "customer_id": "...", ...} on match
                        -> {"found": false, ...} + 404 on miss
GET /health          -> {"ok": true}
GET /_customers      -> list of known customer emails (for debugging only)"""
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote
import json, sys, os

# Test customer DB: email -> record
DB = {
    "dhruv.bais+test1@aktiia.com": {"customer_id": "TEST-001", "name": "Test User One",   "plan": "premium"},
    "dhruv.bais+test2@aktiia.com": {"customer_id": "TEST-002", "name": "Test User Two",   "plan": "basic"},
    "dhruv.bais+test3@aktiia.com": {"customer_id": "TEST-003", "name": "Test User Three", "plan": "premium"},
    "dhruv.bais@aktiia.com":       {"customer_id": "DHRUV-001", "name": "Dhruv Bais",     "plan": "internal"},
}

def normalize(e):
    # decode %2B, also treat literal '+' from application/x-www-form-urlencoded space-conversion carefully
    if e is None: return ""
    e = unquote(e).strip().lower()
    return e

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self._respond(200, {"ok": True, "customers_loaded": len(DB)})
        if parsed.path == "/_customers":
            return self._respond(200, {"emails": sorted(DB.keys())})
        # parse_qs treats + as space; we accept both forms
        # first try raw query with keep_blank_values, then re-normalize with '+' preserved
        raw_qs = parsed.query
        # Rebuild query preserving '+' if it was a literal one (e.g. escaped as %2B)
        qs = parse_qs(raw_qs, keep_blank_values=True)
        email_raw = qs.get("email", [""])[0]
        email = normalize(email_raw)
        # If original had + that got converted to space, restore
        if " " in email and "@" in email:
            email = email.replace(" ", "+")
        if not email:
            return self._respond(400, {"error": "missing email query param", "usage": "?email=x%40y.com"})
        record = DB.get(email)
        if record:
            return self._respond(200, {"found": True, "email": email, **record})
        return self._respond(404, {"found": False, "email": email})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else "10000"))
    print(f"Hilo identity-lookup mock server listening on 0.0.0.0:{port}, {len(DB)} customers loaded", file=sys.stderr)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
