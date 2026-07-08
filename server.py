#!/usr/bin/env python3
"""Hilo identity-lookup mock backend + test page for Intercom soft-identity testing.

Response shape mirrors the real CDP gold table (`researchdb.gold.cdp_obt`, 55 cols)
so this endpoint is a drop-in template for the production identity endpoint that
will eventually query the CDP directly.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote
import json, sys, os, re

# CDP-shape sample records — one row per user, keyed by email for the mock lookup.
# In production, the equivalent query is:
#   SELECT * FROM researchdb.gold.cdp_obt WHERE user_email = :email LIMIT 1
DB = {
    "dhruv.bais+test1@aktiia.com": {
        "user_id": "TEST-001",
        "user_email": "dhruv.bais+test1@aktiia.com",
        "user_email_hash": "3c9f7d1a8b4e2f6c5d8a9b7e1f2c3d4e5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d",
        "user_group": "prod_user",
        "user_gender": "female",
        "user_birth_year": 1985,
        "user_country": "switzerland",
        "user_country_code": "CH",
        "user_created_at": "2024-03-14T09:22:11.000+00:00",
        "user_language": "en",
        "device_os_name": "ios",
        "device_os_version": "17.4",
        "device_type": "Apple iPhone 15 Pro",
        "device_family": "Apple iPhone",
        "app_version": "2.10.1",
        "app_first_event_at": "2024-03-15T07:12:03.421+00:00",
        "app_last_event_at": "2026-07-07T18:44:12.108+00:00",
        "known_band_serial_numbers": ["A77FDBD348"],
        "known_cuff_serial_numbers": ["BA87192201002133"],
        "known_band_lot_numbers": ["L2024-08"],
        "known_cuff_lot_numbers": ["L2024-06"],
        "band_first_sync_at": "2024-03-16T14:11:22.000+00:00",
        "band_last_sync_at": "2026-07-07T18:30:00.000+00:00",
        "cuff_first_sync_at": "2024-03-16T14:05:14.000+00:00",
        "cuff_last_sync_at": "2026-07-06T21:15:47.000+00:00",
        "band_first_init_at": "2024-03-15T07:20:04.000+00:00",
        "band_last_init_at": "2024-11-02T09:14:00.000+00:00",
        "sub_store": "APP_STORE",
        "sub_duration": "annual",
        "sub_type": "premium",
        "sub_price_local": 99.00,
        "sub_renewal_number": 2,
        "is_sub_auto_renewable": True,
        "sub_first_started_at": "2024-03-20T10:00:00.000+00:00",
        "sub_last_started_at": "2026-03-20T10:00:00.000+00:00",
        "sub_last_ended_at": None,
        "sub_last_effective_ended_at": None,
        "sub_last_unsub_at": None,
        "sub_ever_refunded": False,
        "is_cancelled": False,
        "is_churned": False,
        "last_shopify_order_id": "6234567890",
        "last_woocomm_order_id": None,
        "last_shopify_financial_status": "paid",
        "last_shopify_fulfillment_status": "fulfilled",
        "total_order_count": 3,
        "first_ordered_at": "2024-03-14T09:30:00.000+00:00",
        "last_ordered_at": "2025-11-08T14:22:00.000+00:00",
        "is_order_ever_refunded": False,
        "is_order_ever_cancelled": False,
        "is_order_ever_discounted": True,
        "last_order_currency": "CHF",
        "gold_updated_at": "2026-07-08T06:12:53.530+00:00",
        "user_firstname": "Test",
        "user_lastname": "User One",
    },
    "dhruv.bais+test2@aktiia.com": {
        "user_id": "TEST-002",
        "user_email": "dhruv.bais+test2@aktiia.com",
        "user_email_hash": "8a2b9c0d1e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b",
        "user_group": "prod_user",
        "user_gender": "male",
        "user_birth_year": 1972,
        "user_country": "germany",
        "user_country_code": "DE",
        "user_created_at": "2023-11-02T15:41:00.000+00:00",
        "user_language": "de",
        "device_os_name": "android",
        "device_os_version": "14",
        "device_type": "Samsung SM-S928B",
        "device_family": "Samsung Galaxy",
        "app_version": "2.9.4",
        "app_first_event_at": "2023-11-05T10:03:22.000+00:00",
        "app_last_event_at": "2026-05-14T08:11:44.000+00:00",
        "known_band_serial_numbers": ["B48920C11F"],
        "known_cuff_serial_numbers": ["CA92834402100889"],
        "known_band_lot_numbers": ["L2023-11"],
        "known_cuff_lot_numbers": ["L2023-11"],
        "band_first_sync_at": "2023-11-06T09:00:00.000+00:00",
        "band_last_sync_at": "2026-05-14T08:00:00.000+00:00",
        "cuff_first_sync_at": "2023-11-06T09:00:00.000+00:00",
        "cuff_last_sync_at": "2026-04-22T19:12:00.000+00:00",
        "band_first_init_at": "2023-11-05T10:15:00.000+00:00",
        "band_last_init_at": "2023-11-05T10:15:00.000+00:00",
        "sub_store": "PLAY_STORE",
        "sub_duration": "monthly",
        "sub_type": "basic",
        "sub_price_local": 9.90,
        "sub_renewal_number": 8,
        "is_sub_auto_renewable": False,
        "sub_first_started_at": "2023-11-10T00:00:00.000+00:00",
        "sub_last_started_at": "2026-05-10T00:00:00.000+00:00",
        "sub_last_ended_at": "2026-06-10T00:00:00.000+00:00",
        "sub_last_effective_ended_at": "2026-06-10T00:00:00.000+00:00",
        "sub_last_unsub_at": "2026-05-15T12:00:00.000+00:00",
        "sub_ever_refunded": False,
        "is_cancelled": True,
        "is_churned": True,
        "last_shopify_order_id": None,
        "last_woocomm_order_id": "WC-98421",
        "last_shopify_financial_status": None,
        "last_shopify_fulfillment_status": None,
        "total_order_count": 1,
        "first_ordered_at": "2023-11-02T15:45:00.000+00:00",
        "last_ordered_at": "2023-11-02T15:45:00.000+00:00",
        "is_order_ever_refunded": False,
        "is_order_ever_cancelled": False,
        "is_order_ever_discounted": False,
        "last_order_currency": "EUR",
        "gold_updated_at": "2026-07-08T06:12:53.530+00:00",
        "user_firstname": "Test",
        "user_lastname": "User Two",
    },
    "dhruv.bais+test3@aktiia.com": {
        "user_id": "TEST-003",
        "user_email": "dhruv.bais+test3@aktiia.com",
        "user_email_hash": "f1e2d3c4b5a6978869504132a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "user_group": "prod_user",
        "user_gender": "female",
        "user_birth_year": 1990,
        "user_country": "italy",
        "user_country_code": "IT",
        "user_created_at": "2026-06-25T12:00:00.000+00:00",
        "user_language": "it",
        "device_os_name": None,
        "device_os_version": None,
        "device_type": None,
        "device_family": None,
        "app_version": None,
        "app_first_event_at": None,
        "app_last_event_at": None,
        "known_band_serial_numbers": [],
        "known_cuff_serial_numbers": [],
        "known_band_lot_numbers": [],
        "known_cuff_lot_numbers": [],
        "band_first_sync_at": None,
        "band_last_sync_at": None,
        "cuff_first_sync_at": None,
        "cuff_last_sync_at": None,
        "band_first_init_at": None,
        "band_last_init_at": None,
        "sub_store": None,
        "sub_duration": None,
        "sub_type": None,
        "sub_price_local": None,
        "sub_renewal_number": None,
        "is_sub_auto_renewable": None,
        "sub_first_started_at": None,
        "sub_last_started_at": None,
        "sub_last_ended_at": None,
        "sub_last_effective_ended_at": None,
        "sub_last_unsub_at": None,
        "sub_ever_refunded": None,
        "is_cancelled": None,
        "is_churned": None,
        "last_shopify_order_id": "6234599999",
        "last_woocomm_order_id": None,
        "last_shopify_financial_status": "paid",
        "last_shopify_fulfillment_status": "unfulfilled",
        "total_order_count": 1,
        "first_ordered_at": "2026-06-25T12:05:00.000+00:00",
        "last_ordered_at": "2026-06-25T12:05:00.000+00:00",
        "is_order_ever_refunded": False,
        "is_order_ever_cancelled": False,
        "is_order_ever_discounted": False,
        "last_order_currency": "EUR",
        "gold_updated_at": "2026-07-08T06:12:53.530+00:00",
        "user_firstname": "Test",
        "user_lastname": "User Three",
    },
}

INTERCOM_TEST_APP_ID = "pa5i9ru1"  # Aisolv [DEV] - override via ?app=xxx on /test

TEST_PAGE_HTML = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Hilo Messenger - identity test page (CDP shape)</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ background:#0f1115; color:#e6e8ee; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin:0; padding:40px 24px 120px; line-height:1.55; }}
  main {{ max-width:820px; margin:0 auto; }}
  h1 {{ margin:0 0 4px; font-size:26px; }}
  h2 {{ margin-top:32px; font-size:18px; color:#7ab7ff; border-bottom:1px solid #2a2f3a; padding-bottom:6px; }}
  .sub {{ color:#a0a7b4; font-size:14px; }}
  section {{ background:#1a1d25; border:1px solid #2a2f3a; padding:18px 22px; border-radius:8px; margin:16px 0; }}
  table {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
  th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid #2a2f3a; vertical-align:top; }}
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
  <h1>Messenger identity test page</h1>
  <div class="sub">
    Messenger connected to workspace <code>{INTERCOM_TEST_APP_ID}</code>. Response shape mirrors <code>researchdb.gold.cdp_obt</code>. Override the workspace with <code>?app=xxx</code>.
  </div>

  <section>
    <h2>How to test</h2>
    <ol>
      <li>Open this page in an <b>incognito / private window</b> to guarantee a fresh anonymous Lead.</li>
      <li>Click the Intercom widget in the bottom-right corner.</li>
      <li>The Workflow prompts for your email; enter one of the known test emails below.</li>
      <li>Any unknown email returns <code>{{"found": false, ...}}</code> so the workflow branches gracefully.</li>
      <li>In the Intercom Inbox, verify the conversation attaches to the correct User.</li>
    </ol>
  </section>

  <section>
    <h2>Known test emails (CDP shape)</h2>
    <table>
      <thead><tr><th>Email</th><th>user_id</th><th>Country</th><th>Language</th><th>sub_type</th><th>Orders</th></tr></thead>
      <tbody>
        <tr><td><code>dhruv.bais+test1@aktiia.com</code></td><td>TEST-001</td><td>Switzerland</td><td>en</td><td>premium (annual)</td><td>3</td></tr>
        <tr><td><code>dhruv.bais+test2@aktiia.com</code></td><td>TEST-002</td><td>Germany</td><td>de</td><td>basic (cancelled)</td><td>1</td></tr>
        <tr><td><code>dhruv.bais+test3@aktiia.com</code></td><td>TEST-003</td><td>Italy</td><td>it</td><td>none (pre-device)</td><td>1</td></tr>
      </tbody>
    </table>
    <div class="callout">
      Response for a known email returns all 55 CDP columns (identity, device, subscription, commerce). Response for an unknown email returns <code>{{"found": false, "email": "..."}}</code> with HTTP 200 so the Intercom Data Connector doesn't treat it as an error.
    </div>
  </section>

  <section>
    <h2>Backend endpoints</h2>
    <ul>
      <li><span class="pill">GET</span> <code>/?email=&lt;email&gt;</code> - CDP-shaped lookup</li>
      <li><span class="pill">GET</span> <code>/health</code> - health check</li>
      <li><span class="pill">GET</span> <code>/_customers</code> - list known emails (debug)</li>
      <li><span class="pill">GET</span> <code>/_schema</code> - column names returned in a match response</li>
      <li><span class="pill">GET</span> <code>/test</code> - this page</li>
    </ul>
  </section>

  <div class="callout good">
    Backend URL: <code>https://hilo-identity-mock.onrender.com</code> - point the Intercom Data Connector at this.
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

# Canonical CDP schema column list (from Databricks CDP doc: 55 columns of gold.cdp_obt)
CDP_COLUMNS = [
    "user_id","user_email","user_email_hash","user_group","user_gender","user_birth_year",
    "user_country","user_country_code","user_created_at","user_language",
    "device_os_name","device_os_version","device_type","device_family","app_version",
    "app_first_event_at","app_last_event_at",
    "known_band_serial_numbers","known_cuff_serial_numbers","known_band_lot_numbers","known_cuff_lot_numbers",
    "band_first_sync_at","band_last_sync_at","cuff_first_sync_at","cuff_last_sync_at",
    "band_first_init_at","band_last_init_at",
    "sub_store","sub_duration","sub_type","sub_price_local","sub_renewal_number","is_sub_auto_renewable",
    "sub_first_started_at","sub_last_started_at","sub_last_ended_at","sub_last_effective_ended_at","sub_last_unsub_at",
    "sub_ever_refunded","is_cancelled","is_churned",
    "last_shopify_order_id","last_woocomm_order_id","last_shopify_financial_status","last_shopify_fulfillment_status",
    "total_order_count","first_ordered_at","last_ordered_at",
    "is_order_ever_refunded","is_order_ever_cancelled","is_order_ever_discounted","last_order_currency",
    "gold_updated_at","user_firstname","user_lastname",
]

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
            qs_here = parse_qs(parsed.query, keep_blank_values=True)
            app_override = qs_here.get("app", [""])[0].strip()
            html_out = TEST_PAGE_HTML
            if app_override and re.fullmatch(r"[a-zA-Z0-9]{4,20}", app_override):
                html_out = TEST_PAGE_HTML.replace(INTERCOM_TEST_APP_ID, app_override)
            return self._html(200, html_out)
        if parsed.path == "/health":
            return self._json(200, {"ok": True, "customers_loaded": len(DB), "schema_columns": len(CDP_COLUMNS)})
        if parsed.path == "/_customers":
            return self._json(200, {"emails": sorted(DB.keys())})
        if parsed.path == "/_schema":
            return self._json(200, {"columns": CDP_COLUMNS, "count": len(CDP_COLUMNS)})

        qs = parse_qs(parsed.query, keep_blank_values=True)
        email_raw = qs.get("email", [""])[0]
        email = normalize(email_raw)
        if " " in email and "@" in email:
            email = email.replace(" ", "+")

        if not email:
            if parsed.path == "/":
                return self._html(200, "<html><body style='background:#0f1115;color:#e6e8ee;font-family:sans-serif;padding:40px;'><h1>Hilo identity mock (CDP shape)</h1><p>See <a href='/test' style='color:#7ab7ff'>/test</a> for the test page, <a href='/_schema' style='color:#7ab7ff'>/_schema</a> for the response columns, or <a href='/_customers' style='color:#7ab7ff'>/_customers</a> for known emails.</p></body></html>")
            return self._json(400, {"error": "missing email query param", "usage": "?email=x%40y.com"})

        record = DB.get(email)
        if record:
            # Return CDP-shaped record with a `found:true` wrapper. Also expose top-level
            # convenience fields the Workflow can bind to directly.
            resp = {"found": True, "email": email}
            resp.update(record)
            return self._json(200, resp)
        # Miss: return HTTP 200 with found:false so Intercom's Data Connector treats it as a valid response
        return self._json(200, {"found": False, "email": email})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else "10000"))
    print(f"Hilo identity mock listening on 0.0.0.0:{port}, {len(DB)} customers loaded, {len(CDP_COLUMNS)}-col CDP schema", file=sys.stderr)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
