"""Quickstart client for Quiet Node v0.1.

Creates a session, polls /observe until OPEN, claims if possible,
and prints the reflection-pack questions.

Usage:
    python -m tools.quickstart_client
    python -m tools.quickstart_client --base-url http://localhost:9000
"""

import argparse
import sys
import time

import httpx


def main():
    parser = argparse.ArgumentParser(description="Quiet Node quickstart client")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--max-polls", type=int, default=60, help="Max /observe polls before giving up")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Seconds between polls")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    client = httpx.Client(base_url=base, timeout=30)

    # 1. Create session
    print("--- Creating session ---")
    resp = client.post("/session/new")
    resp.raise_for_status()
    session = resp.json()
    token = session["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  session_id:  {session['session_id']}")
    print(f"  syn_balance: {session['syn_balance']}")

    # 2. Poll /observe
    print(f"\n--- Polling /observe (max {args.max_polls} attempts) ---")
    claim_token = None
    for i in range(1, args.max_polls + 1):
        resp = client.get("/observe", headers=headers)
        if resp.status_code == 402:
            print(f"  [{i}] 402 — starved, stopping.")
            break
        resp.raise_for_status()
        body = resp.json()
        state = body["state"]
        if state == "OPEN":
            claim_token = body["claim_token"]
            print(f"  [{i}] OPEN — claim_token: {claim_token}")
            break
        else:
            entropy_size = len(body.get("entropy", "")) // 2
            print(f"  [{i}] DORMANT  (entropy: {entropy_size} bytes)")
        time.sleep(args.poll_interval)

    # 3. Claim
    if claim_token:
        print("\n--- Claiming reward ---")
        resp = client.post("/claim", headers=headers, json={"token": claim_token})
        resp.raise_for_status()
        result = resp.json()
        if result["success"]:
            print(f"  Claimed! +{result['reward']} SYN  (balance: {result['syn_balance']})")
        else:
            print(f"  Failed: {result['reason']}  (penalty: {result.get('penalty', 0)})")
    else:
        print("\n  No OPEN window found within poll limit.")

    # 4. Telemetry
    print("\n--- Telemetry ---")
    resp = client.get("/session/me/telemetry", headers=headers)
    if resp.status_code == 200:
        t = resp.json()
        print(f"  requests:    {t['request_count']}")
        print(f"  bytes:       {t['total_bytes']}")
        print(f"  syn_balance: {t['syn_balance']}")
        print(f"  burn_rate:   {t['burn_rate_estimate']}")
        print(f"  claims:      {t['claim_successes']}/{t['claim_attempts']} succeeded")

    # 5. Reflection pack
    print("\n--- Reflection Pack ---")
    resp = client.get("/session/me/reflection-pack", headers=headers)
    if resp.status_code == 200:
        pack = resp.json()
        if pack["notable_moments"]:
            print("  Notable moments:")
            for m in pack["notable_moments"]:
                print(f"    - {m['type']}: {m}")
        print("  Questions:")
        for q in pack["reflection_questions"]:
            print(f"    ? {q}")
    else:
        print(f"  (skipped — status {resp.status_code})")

    print("\n--- Done ---")


if __name__ == "__main__":
    main()
