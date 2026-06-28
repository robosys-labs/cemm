import urllib.request
import urllib.error
import json
import time

API_KEY = "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"
URL = "https://integrate.api.nvidia.com/v1/chat/completions"

TEST_PROMPT = "Extract entities and claims from: 'Alice asked Bob about the PostgreSQL database performance issues yesterday.' Return JSON only."

models_to_test = [
    # Already confirmed working
    ("meta/llama-3.1-8b-instruct", "small"),
    ("meta/llama-3.3-70b-instruct", "large"),
    # From catalog - small/fast options
    ("meta/llama-3.2-3b-instruct", "small"),
    ("google/gemma-3-4b-it", "small"),
    ("google/gemma-2-2b-it", "small"),
    ("mistralai/mixtral-8x7b-instruct-v0.1", "medium"),
    ("microsoft/phi-4-mini-instruct", "small"),
    ("qwen/qwen3-next-80b-a3b-instruct", "medium"),
    # From catalog - large/quality options
    ("meta/llama-3.1-70b-instruct", "large"),
    ("meta/llama-4-maverick-17b-128e-instruct", "large"),
    ("mistralai/mistral-large", "large"),
    ("google/gemma-3-12b-it", "medium"),
    ("nvidia/llama-3.1-nemotron-51b-instruct", "large"),
    # Re-test these (were in catalog but got 404 earlier)
    ("mistralai/mistral-7b-instruct-v0.3", "small"),
    ("nvidia/llama-3.1-nemotron-70b-instruct", "large"),
    ("nvidia/nemotron-4-340b-instruct", "large"),
]


def test_model(model_id, category):
    print(f"\n{'='*70}")
    print(f"TESTING: {model_id}  [{category}]")
    print(f"{'='*70}")

    payload = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": TEST_PROMPT}],
        "temperature": 0.1,
        "max_tokens": 500,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    result = {
        "model": model_id,
        "category": category,
        "status": "unknown",
        "error": None,
        "response_time": None,
        "json_valid": False,
        "has_entities": False,
        "has_claims": False,
        "first_200_chars": "",
    }

    try:
        start = time.time()
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            result["response_time"] = round(time.time() - start, 2)

        data = json.loads(body)

        if "error" in data:
            result["status"] = "failure"
            result["error"] = data["error"].get("message", str(data["error"]))
            print(f"  FAILURE: {result['error']}")
            return result

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        result["first_200_chars"] = content[:200]

        # Extract JSON from response
        content_clean = content.strip()
        if "```json" in content_clean:
            content_clean = content_clean.split("```json")[1].split("```")[0].strip()
        elif "```" in content_clean:
            content_clean = content_clean.split("```")[1].split("```")[0].strip()
        # Try parsing from first { to last }
        if "{" in content_clean and "}" in content_clean:
            start_idx = content_clean.index("{")
            end_idx = content_clean.rindex("}") + 1
            content_clean = content_clean[start_idx:end_idx]

        try:
            parsed = json.loads(content_clean)
            result["json_valid"] = True
            if isinstance(parsed, dict):
                result["has_entities"] = "entities" in parsed
                result["has_claims"] = "claims" in parsed
        except json.JSONDecodeError:
            result["json_valid"] = False

        result["status"] = "success"
        print(f"  Status: SUCCESS")
        print(f"  Time: {result['response_time']}s")
        print(f"  JSON valid: {'YES' if result['json_valid'] else 'NO'}")
        print(f"  Has entities: {'YES' if result['has_entities'] else 'NO'}")
        print(f"  Has claims: {'YES' if result['has_claims'] else 'NO'}")
        print(f"  First 200: {result['first_200_chars'][:200]}")

    except urllib.error.HTTPError as e:
        result["status"] = "failure"
        body = e.read().decode("utf-8", errors="replace")
        try:
            err_data = json.loads(body)
            result["error"] = err_data.get("error", {}).get("message", body[:300])
        except json.JSONDecodeError:
            result["error"] = body[:300]
        print(f"  FAILURE (HTTP {e.code}): {result['error']}")

    except urllib.error.URLError as e:
        result["status"] = "failure"
        result["error"] = str(e.reason)
        print(f"  FAILURE: {result['error']}")

    except Exception as e:
        result["status"] = "failure"
        result["error"] = str(e)
        print(f"  FAILURE: {result['error']}")

    return result


def main():
    all_results = []
    for model_id, category in models_to_test:
        r = test_model(model_id, category)
        all_results.append(r)

    # Print summary table
    print(f"\n\n{'='*105}")
    print("SUMMARY TABLE")
    print(f"{'='*105}")
    header = f"{'Model':<50} {'Cat':<8} {'Status':<10} {'Time(s)':<10} {'JSON':<6} {'Ent':<6} {'Claim':<6}"
    print(header)
    print("-" * 105)
    for r in all_results:
        status = r["status"]
        t = str(r.get("response_time", "N/A")) if r["response_time"] else "ERR"
        j = "Y" if r["json_valid"] else "N"
        e = "Y" if r["has_entities"] else "N"
        c = "Y" if r["has_claims"] else "N"
        print(f"{r['model']:<50} {r['category']:<8} {status:<10} {t:<10} {j:<6} {e:<6} {c:<6}")

    # Recommendations
    print(f"\n\nRECOMMENDATIONS:")
    print(f"  Fast & reliable: {[r['model'] for r in all_results if r['status'] == 'success' and r['response_time'] and r['response_time'] < 3]}")
    print(f"  Quality & reliable: {[r['model'] for r in all_results if r['status'] == 'success' and r['json_valid'] and r['has_entities'] and r['has_claims']]}")
    print(f"  Failed (access/availability): {[r['model'] for r in all_results if r['status'] == 'failure']}")

if __name__ == "__main__":
    main()
