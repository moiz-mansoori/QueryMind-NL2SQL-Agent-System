"""Quick test of all Week 3 Day 1 API endpoints."""
import httpx
import json
import sys

BASE = "http://127.0.0.1:8000"

def test(label, method, url, body=None):
    print(f"\n{'='*60}")
    print(f"[TEST] {label}")
    print(f"  {method} {url}")
    try:
        if method == "GET":
            r = httpx.get(url, timeout=60)
        else:
            r = httpx.post(url, json=body, timeout=120)
        print(f"  Status: {r.status_code}")
        data = r.json()
        print(f"  Response: {json.dumps(data, indent=2, default=str)[:800]}")
        return r.status_code == 200
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

results = []

# 1. Health check
results.append(("Health Check", test("Health Check", "GET", f"{BASE}/health")))

# 2. Analytics Summary
results.append(("Analytics Summary", test("Analytics Summary", "GET", f"{BASE}/analytics/summary")))

# 3. Analytics History
results.append(("Analytics History", test("Analytics History", "GET", f"{BASE}/analytics/history?limit=5")))

# 4. Analytics Failures
results.append(("Analytics Failures", test("Analytics Failures", "GET", f"{BASE}/analytics/failures?limit=5")))

# 5. Analytics Slow Queries
results.append(("Slow Queries", test("Slow Queries", "GET", f"{BASE}/analytics/slow-queries?threshold_ms=1000&limit=5")))

# 6. POST /query (the big one)
results.append(("POST /query", test(
    "POST /query — How many customers?",
    "POST", f"{BASE}/query",
    body={"question": "How many customers are there?"}
)))

# 7. Trace endpoint
# We use ID 1 from the history (assumes there is at least 1 query logged)
results.append(("Trace Query 1", test(
    "GET /analytics/trace/1",
    "GET", f"{BASE}/analytics/trace/1"
)))

# 8. Queries per day chart data
results.append(("Queries Per Day", test(
    "GET /analytics/queries-per-day",
    "GET", f"{BASE}/analytics/queries-per-day?days=7"
)))

# 9. Validation test — too short question
results.append(("Validation", test(
    "POST /query — Validation (too short)",
    "POST", f"{BASE}/query",
    body={"question": "Hi"}
)))

# 10. Rebuild embeddings
results.append(("Rebuild Embeddings", test(
    "POST /embeddings/rebuild",
    "POST", f"{BASE}/embeddings/rebuild"
)))

print(f"\n{'='*60}")
print("RESULTS SUMMARY")
print(f"{'='*60}")
for name, passed in results:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {name:25} : {status}")

passed = sum(1 for _, p in results if p)
total = len(results)
print(f"\n  Total: {passed}/{total} passed")
