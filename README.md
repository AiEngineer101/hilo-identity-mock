# hilo-identity-mock

Mock identity-lookup backend for testing Intercom's soft-identity conversation merging.

- `GET /?email=x` -> `{"found": true, "customer_id": ...}` on match, 404 otherwise
- `GET /health` -> `{"ok": true}`
- `GET /_customers` -> list of known test emails
