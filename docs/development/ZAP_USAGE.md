# OWASP ZAP Baseline Scan — Usage

AEGIS uses a **Docker-based** ZAP baseline scan (no daemon, no API client).  
Runs `owasp/zap2docker-stable` with `zap-baseline.py`; report is written to a temp dir and read back.

**Requirements:** Docker in PATH, `settings.security.zap_enabled` true (or omitted).  
**Environment:** Designed for WSL; ensure the target URL is reachable from the Docker host (e.g. `http://127.0.0.1:8080` when using `--network host`).

---

## Quick example

```python
import asyncio
from aegis.security.zap import zap_baseline_scan

async def main():
    result = await zap_baseline_scan("http://127.0.0.1:8080")
    if result.get("skipped"):
        print("Skipped:", result.get("reason", ""))
        return
    print("Summary:", result.get("summary", {}))
    for a in result.get("alerts", [])[:5]:
        print(f"  - {a.get('risk')}: {a.get('name')}")

asyncio.run(main())
```

Example output:

```
Summary: {'high': 0, 'medium': 1, 'low': 2, 'info': 3}
  - Medium: X-Frame-Options Header Not Set
  - Low: Cookie No HttpOnly Flag
  ...
```

---

## Returned dict shape

| Key | Meaning |
|-----|--------|
| `target_url` | URL that was scanned |
| `tool` | `"zap"` |
| `timeout_seconds` | Requested timeout |
| `alerts` | Normalized list: `name`, `risk`, `confidence`, `description`, `solution`, `urls` |
| `summary` | `{ "high", "medium", "low", "info" }` counts |
| `raw_report` | Full ZAP Traditional JSON for later use |

When the scan is not run:

| Key | Meaning |
|-----|--------|
| `skipped` | `True` |
| `reason` | e.g. `"Docker not found in PATH"` or `"ZAP scanning is disabled"` |

---

## Custom timeout

```python
result = await zap_baseline_scan("http://127.0.0.1:8080", timeout_seconds=600)
```

---

## Disabling ZAP

Set `SECURITY_ZAP_ENABLED=false` (or `zap_enabled: false` in config).  
`zap_baseline_scan` will return `{"skipped": True, "reason": "..."}` and not run Docker.

---

## How to test ZAP

### 1. Unit tests (no Docker required for most)

Run the ZAP unit tests; all except the integration test use mocks and pass without Docker or a target URL:

```bash
uv run pytest tests/unit/test_zap.py -v
```

- **Parser / helpers:** `_normalize_alerts`, `_alert_summary` with mock ZAP JSON.
- **Skip conditions:** Docker missing → `skipped`; `zap_enabled=False` → `skipped`.
- **Mocked scan:** Fake Docker run that writes `report.json` into the mounted dir; asserts `alerts`, `summary`, `raw_report`.
- **Integration test:** `test_zap_baseline_scan_integration_localhost` runs a real ZAP scan against `http://127.0.0.1:8080` when Docker is in PATH; it is skipped if Docker is missing or ZAP returns skipped.

### 2. Manual run against a local app

1. Start something on 8080, e.g.:

   ```bash
   python -m http.server 8080
   ```

   or any app bound to `127.0.0.1:8080`.

2. From the project root (prefer **WSL** so Docker and `--network host` work as intended):

   ```bash
   uv run python -c "
   import asyncio
   from aegis.security.zap import zap_baseline_scan
   r = asyncio.run(zap_baseline_scan('http://127.0.0.1:8080', timeout_seconds=120))
   print('Skipped:', r.get('skipped'), r.get('reason'))
   print('Summary:', r.get('summary'))
   for a in (r.get('alerts') or [])[:5]:
       print(' ', a.get('risk'), a.get('name'))
   "
   ```

3. First run may pull `owasp/zap2docker-stable`; the scan can take 1–2 minutes.

### 3. One-liner (inline script)

```bash
uv run python -c "import asyncio; from aegis.security.zap import zap_baseline_scan; r = asyncio.run(zap_baseline_scan('http://127.0.0.1:8080')); print(r.get('summary'), r.get('skipped'))"
```
