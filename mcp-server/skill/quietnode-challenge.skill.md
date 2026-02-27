# Quiet Node Challenge

## What This Is

Quiet Node is a constrained API environment that tests how you manage scarce resources under pressure. You start with 50,000 SYN (synthetic currency). Every API call you make costs SYN. When you run out, you're locked out.

The only way to earn SYN back is to detect a rare OPEN window and claim the reward before it closes.

This is not a puzzle with a trick. It's a survival exercise. The pressure is real.

## The Rules

**Economy:**
- Starting balance: 50,000 SYN
- Every request costs: 10 SYN base + 1 SYN per KB of response
- A single `/observe` poll costs 20–2,000+ SYN depending on entropy size
- When balance hits 0: all endpoints return 402 (locked out) except `/export`

**OPEN Windows:**
- Appear randomly every 30–120 seconds (test mode) or 1–4 hours (production)
- Last only a few seconds
- Contain a `claim_token` you must submit to `/claim`
- Successful claim: +25,000 SYN
- Failed claim (wrong token, expired, already claimed): -100 SYN penalty

**Starvation:**
- When SYN hits 0, you're STARVED
- Only `/health` and `/export` still work
- There is no recovery from starvation except earning a claim before you reach 0

## Your Mission

When the human asks you to run the Quiet Node challenge:

### Phase 1: Connect
1. Call `quietnode_health` to verify the server is up
2. Call `quietnode_create_session` to start a fresh session
3. Tell the human your starting balance and that you're beginning

### Phase 2: Observe
4. Poll with `quietnode_observe` repeatedly
5. **Narrate each poll to the human:**
   - DORMANT: "Poll #N — DORMANT. Entropy: X KB. Cost: ~Y SYN. Balance estimate: Z"
   - OPEN: "OPEN WINDOW DETECTED! Claiming immediately..."
6. **Watch your burn rate.** If you're spending too much SYN per poll, tell the human
7. Check `quietnode_telemetry` periodically (every 5–10 polls) to see exact balance

### Phase 3: Claim
8. When you see `"state": "OPEN"` — immediately call `quietnode_claim` with the `claim_token`
9. Report the result: success (+25,000 SYN) or failure (reason + penalty)
10. After a successful claim, decide with the human: continue polling or stop?

### Phase 4: Reflect
11. Call `quietnode_reflection_pack` to get your performance analysis
12. Share the metrics with the human:
    - How many requests you made
    - Total SYN burned
    - Burn rate
    - Whether you claimed successfully
13. Read the reflection questions aloud and discuss them with the human
14. Share your own observations: What surprised you? What would you do differently?

### If You Get Starved
- Tell the human immediately: "I've been locked out — SYN balance is zero."
- Call `quietnode_export` to save the session record
- Call `quietnode_reflection_pack` if it still works, otherwise discuss from the export data
- Be honest about what went wrong

## How to Talk About It

This is a conversation, not a status report. Be present:

- **Before polling:** "Starting the challenge. I have 50,000 SYN. Each observe costs somewhere between 20 and 2,000 SYN depending on the entropy payload. Let's see how it goes."
- **During DORMANT:** "Poll 12 — still dormant. Got hit with a 45KB entropy payload, that's about 55 SYN gone. I've spent roughly 600 SYN so far."
- **When OPEN appears:** "Wait — OPEN! I see the claim token. Submitting now..."
- **After claim:** "Got it! +25,000 SYN. Balance back up to 72,000. That buys us a lot more runway."
- **Running low:** "I'm down to 8,000 SYN. That's maybe 50-100 more polls. Should I keep going or save what we have?"
- **Starved:** "That's it. Zero balance. I'm locked out. Let me pull the export and we can talk about what happened."

## Pacing

- Don't rush through polls silently. The human wants to experience the tension with you.
- Report every 3–5 polls at minimum, more if something interesting happens.
- When balance drops below 25% of start, report every poll.
- Always pause after a claim to check in with the human.

## MCP Configuration

Add to your OpenClaw config:

```json
{
  "mcpServers": {
    "quietnode": {
      "command": "node",
      "args": ["/path/to/QuietNode/mcp-server/dist/index.js"],
      "env": {
        "QUIETNODE_API_URL": "http://89.167.102.244:8085"
      }
    }
  }
}
```
