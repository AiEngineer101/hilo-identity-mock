#!/usr/bin/env python3
"""Hilo identity-lookup mock backend + test page for Intercom soft-identity testing."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote
import json, sys, os, re

DB = {
    "dhruv.bais+test1@aktiia.com": {"customer_id": "TEST-001", "name": "Test User One",   "plan": "premium"},
    "dhruv.bais+test2@aktiia.com": {"customer_id": "TEST-002", "name": "Test User Two",   "plan": "basic"},
    "dhruv.bais+test3@aktiia.com": {"customer_id": "TEST-003", "name": "Test User Three", "plan": "premium"},
    "dhruv.bais@aktiia.com":       {"customer_id": "DHRUV-001", "name": "Dhruv Bais",     "plan": "internal"},
}

INTERCOM_TEST_APP_ID = "pa5i9ru1"  # Aisolv [DEV] — override via ?app=xxx on /test

TEST_PAGE_HTML = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Hilo Messenger Test - soft-identity flow</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ background:#0f1115; color:#e6e8ee; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin:0; padding:40px 24px 120px; line-height:1.55; }}
  main {{ max-width:820px; margin:0 auto; }}
  h1 {{ margin:0 0 4px; font-size:26px; }}
  h2 {{ margin-top:32px; font-size:18px; color:#7ab7ff; border-bottom:1px solid #2a2f3a; padding-bottom:6px; }}
  .sub {{ color:#a0a7b4; font-size:14px; }}
  section {{ background:#1a1d25; border:1px solid #2a2f3a; padding:18px 22px; border-radius:8px; margin:16px 0; }}
  table {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
  th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid #2a2f3a; }}
  th {{ color:#a0a7b4; font-weight:600; font-size:11.5px; text-transform:uppercase; letter-spacing:.03em; }}
  code {{ background:#0d0f14; padding:1px 6px; border-radius:3px; font-size:12.5px; }}
  .callout {{ background:#20232c; border-left:3px solid #c07a2b; padding:10px 14px; border-radius:4px; margin:12px 0; font-size:13.5px; }}
  .callout.good {{ border-left-color:#4c8b4c; }}
  ol li, ul li {{ margin:6px 0; }}
  .pill {{ display:inline-block; background:#2a2f3a; padding:2px 10px; border-radius:12px; font-size:12px; margin-right:6px; }}
</style>
</head>
<body>
<main>
  <h1>Hilo Messenger - identity test page</h1>
  <div class="sub">
    Messenger connected to workspace <code>{INTERCOM_TEST_APP_ID}</code> (Hilo [TEST]). Click the widget bottom-right to open a chat and step through the identity Workflow.
  </div>

  <section>
    <h2>How to test</h2>
    <ol>
      <li>Open this page in an <b>incognito / private window</b> to guarantee a fresh anonymous Lead.</li>
      <li>Click the Intercom widget in the bottom-right corner.</li>
      <li>The Workflow (once set live in Intercom) will prompt for your email.</li>
      <li>Enter one of the known test emails below to trigger the identify path.</li>
      <li>Enter any unknown email (e.g. <code>stranger@nowhere.com</code>) to test the graceful fallback.</li>
      <li>In the Intercom Inbox for the Hilo [TEST] workspace, verify the conversation is attached to the correct User (not a fresh Lead).</li>
    </ol>
  </section>

  <section>
    <h2>Known test emails</h2>
    <table>
      <thead><tr><th>Email</th><th>Expected customer_id</th><th>Name</th><th>Plan</th></tr></thead>
      <tbody>
        <tr><td><code>dhruv.bais+test1@aktiia.com</code></td><td>TEST-001</td><td>Test User One</td><td>premium</td></tr>
        <tr><td><code>dhruv.bais+test2@aktiia.com</code></td><td>TEST-002</td><td>Test User Two</td><td>basic</td></tr>
        <tr><td><code>dhruv.bais+test3@aktiia.com</code></td><td>TEST-003</td><td>Test User Three</td><td>premium</td></tr>
      </tbody>
    </table>
    <div class="callout">
      <b>Note on <code>+</code>:</b> emails with a plus alias must be URL-encoded as <code>%2B</code> when passed as a query parameter. Intercom's Data Connector should handle this automatically. The mock backend accepts both encoded and literal forms.
    </div>
  </section>

  <section>
    <h2>Backend endpoints (mock)</h2>
    <ul>
      <li><span class="pill">GET</span> <code>/?email=&lt;email&gt;</code> - lookup, returns 200 with customer info or 404</li>
      <li><span class="pill">GET</span> <code>/health</code> - health check</li>
      <li><span class="pill">GET</span> <code>/_customers</code> - list known emails (debug)</li>
      <li><span class="pill">GET</span> <code>/test</code> - this page</li>
    </ul>
  </section>

  <section>
    <h2>What to verify in Intercom</h2>
    <ul>
      <li><b>Known email:</b> Lead should be upgraded to the User with matching <code>external_id</code>. Conversation attached to that User.</li>
      <li><b>Unknown email:</b> Stays a Lead. Workflow gracefully continues (no error).</li>
      <li><b>Merging:</b> After identifying, open a second incognito session and go through the flow again with the same email. In the Inbox, both conversations should now belong to the same User, and merging via <code>Cmd+K -> Merge into</code> should work.</li>
    </ul>
  </section>

  <div class="callout good">
    Mock backend URL: <code>https://hilo-identity-mock.onrender.com</code> - point the Intercom Data Connector at this.
  </div>
</main>

<script>
  window.intercomSettings = {{ app_id: "{INTERCOM_TEST_APP_ID}" }};
  (function(){{var w=window;var ic=w.Intercom;if(typeof ic==="function"){{ic('reattach_activator');ic('update',w.intercomSettings);}}else{{var d=document;var i=function(){{i.c(arguments);}};i.q=[];i.c=function(args){{i.q.push(args);}};w.Intercom=i;var l=function(){{var s=d.createElement('script');s.type='text/javascript';s.async=true;s.src='https://widget.intercom.io/widget/{INTERCOM_TEST_APP_ID}';var x=d.getElementsByTagName('script')[0];x.parentNode.insertBefore(s,x);}};if(document.readyState==='complete'){{l();}}else if(w.attachEvent){{w.attachEvent('onload',l);}}else{{w.addEventListener('load',l,false);}}}}}})();
</script>
</body>
</html>"""

def normalize(e):
    if e is None: return ""
    e = unquote(e).strip().lower()
    return e

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _json(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def _html(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/test", "/test/"):
            # Allow ?app=xxx to override the Messenger app_id at request time
            qs_here = parse_qs(parsed.query, keep_blank_values=True)
            app_override = qs_here.get("app", [""])[0].strip()
            html_out = TEST_PAGE_HTML
            if app_override and re.fullmatch(r"[a-zA-Z0-9]{4,20}", app_override):
                html_out = TEST_PAGE_HTML.replace(INTERCOM_TEST_APP_ID, app_override)
            return self._html(200, html_out)
        if parsed.path == "/health":
            return self._json(200, {"ok": True, "customers_loaded": len(DB)})
        if parsed.path == "/_customers":
            return self._json(200, {"emails": sorted(DB.keys())})

        # Lookup endpoint
        qs = parse_qs(parsed.query, keep_blank_values=True)
        email_raw = qs.get("email", [""])[0]
        email = normalize(email_raw)
        if " " in email and "@" in email:
            email = email.replace(" ", "+")

        if not email:
            # Root with no email query: show a friendly hint pointing to /test
            if parsed.path == "/":
                return self._html(200, "<html><body style='background:#0f1115;color:#e6e8ee;font-family:sans-serif;padding:40px;'><h1>Hilo identity mock</h1><p>See <a href='/test' style='color:#7ab7ff'>/test</a> for the test page, or <a href='/_customers' style='color:#7ab7ff'>/_customers</a> for known emails.</p></body></html>")
            return self._json(400, {"error": "missing email query param", "usage": "?email=x%40y.com"})

        record = DB.get(email)
        if record:
            return self._json(200, {"found": True, "email": email, **record})
        return self._json(404, {"found": False, "email": email})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else "10000"))
    print(f"Hilo identity mock listening on 0.0.0.0:{port}, {len(DB)} customers loaded", file=sys.stderr)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
