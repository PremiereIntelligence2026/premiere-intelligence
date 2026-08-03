#!/usr/bin/env python3
"""
Generates the daily audio from latest_briefing.json.
Uses Claude to write a conversational podcast script, then OpenAI TTS to voice it.
"""
import os, json, httpx

OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
AUDIO_DIR         = "audio"

print(f"Audio key length: {len(OPENAI_API_KEY)}")
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY missing")
    raise SystemExit(1)

with open("latest_briefing.json") as f:
    data = json.load(f)

date_slug = data["date_slug"]

# ── Generate conversational script via Claude ─────────────────────────────────
stories_text = "\n\n".join(
    f"- {s['headline']} ({s['source']}, {s.get('date','')}): {s['summary']}"
    for s in sorted(data["stories"], key=lambda x: -x["score"])
)

prompt = f"""You are writing a spoken podcast script for a TTS voice. Write EXACTLY as someone would naturally SPEAK — not as someone would write.

Specific techniques you MUST use:
- Very short sentences. Like this. Two or three words sometimes.
- Rhetorical questions: "So what does this actually mean for luxury brands?"
- Pause markers using ellipses: "And here's the thing... this changes everything."
- Direct address: "If you're managing media budgets right now, pay attention to this one."
- Reactions and opinions: "Honestly, this caught me off guard." or "This is the one I keep thinking about."
- Vary sentence length dramatically — mix punchy short ones with longer flowing ones
- Natural connectors: "But here's what's interesting.", "Now, separately...", "Which brings me to..."
- NO formal language. NO jargon without explanation. NO lists.

CRITICAL — STORY TRANSITIONS: Each story must be clearly introduced with a verbal signpost so the listener knows a new story is starting. Use phrases like:
- "Story one."
- "Moving to story two."
- "Third story today."
- "Number four."
- "And finally, story five."
These signposts must come at the START of each new story, before any content. This is essential so listeners can follow along.

Format: Pure spoken words only. No stage directions. No headers. Just speech.
Length: About 2 minutes when spoken aloud (roughly 300 words).

Today: {data['date']}
Opening signal: {data['lede']}

Stories to cover:
{stories_text}

Write the script now, starting with a warm good morning greeting:"""

if ANTHROPIC_API_KEY:
    print("Generating conversational script via Claude...")
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-haiku-4-5", "max_tokens": 1000, "messages": [{"role": "user", "content": prompt}]},
        timeout=30,
    )
    r.raise_for_status()
    script = r.json()["content"][0]["text"].strip()
    print(f"Script length: {len(script)} chars")
else:
    # Fallback: simple script without Claude
    print("No Anthropic key — using simple script")
    parts = [f"Good morning. Today is {data['date']}. Welcome to Première Intelligence.",
             f"{data['lede']}"]
    for s in sorted(data["stories"], key=lambda x: -x["score"]):
        parts.append(f"{s['headline']}. {s['summary']}")
    parts.append("That's your briefing. Stay sharp.")
    script = " ".join(parts)

# Truncate to OpenAI's 4096 char limit
script = script[:4096]

# ── Generate audio via OpenAI TTS ─────────────────────────────────────────────
os.makedirs(AUDIO_DIR, exist_ok=True)
print("Calling OpenAI TTS...")
r = httpx.post(
    "https://api.openai.com/v1/audio/speech",
    headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
    json={"model": "tts-1", "input": script, "voice": "fable"},
    timeout=60,
)
print(f"OpenAI status: {r.status_code}")
r.raise_for_status()

mp3_path = f"{AUDIO_DIR}/{date_slug}.mp3"
with open(mp3_path, "wb") as f:
    f.write(r.content)
print(f"✓ Audio saved → {mp3_path}")

# ── Generate HTML landing page ─────────────────────────────────────────────
html_path = f"{AUDIO_DIR}/{date_slug}.html"
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Première Intelligence — {data['date']}</title>
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ background:#f5e6e0; font-family:'Helvetica Neue',Arial,sans-serif; min-height:100vh; display:flex; align-items:center; justify-content:center; padding:40px 20px; }}
    .card {{ max-width:560px; width:100%; }}
    .date {{ font-size:9px; letter-spacing:0.18em; text-transform:uppercase; color:#7a6358; margin-bottom:12px; }}
    .title {{ font-family:Georgia,serif; font-size:52px; font-weight:700; line-height:0.9; color:#1a1410; margin-bottom:6px; }}
    .tagline {{ font-size:9px; letter-spacing:0.2em; text-transform:uppercase; color:#7a6358; margin-bottom:20px; padding-bottom:20px; border-bottom:2px solid #1a1410; }}
    .lede {{ font-family:Georgia,serif; font-style:italic; font-size:15px; line-height:1.6; color:#1a1410; margin-bottom:28px; }}
    audio {{ width:100%; margin-bottom:8px; }}
    .credit {{ font-size:9px; letter-spacing:0.14em; text-transform:uppercase; color:#c9b5a8; text-align:center; margin-top:32px; }}
  </style>
</head>
<body>
  <div class="card">
    <p class="date">{data['date']}</p>
    <div class="title">PREMIÈRE<br>INTELLIGENCE</div>
    <p class="tagline">The luxury-tech briefing</p>
    <p class="lede">{data['lede']}</p>
    <audio controls autoplay>
      <source src="{date_slug}.mp3" type="audio/mpeg">
    </audio>
    <p class="credit">Première Intelligence &nbsp;·&nbsp; The luxury-tech briefing</p>
  </div>
</body>
</html>"""

with open(html_path, "w") as f:
    f.write(html)
print(f"✓ Landing page saved → {html_path}")
