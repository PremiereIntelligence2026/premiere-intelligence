#!/usr/bin/env python3
"""
Premiere Intelligence - Daily Email Briefing
Runs every weekday at 7:30 AM ET via GitHub Actions.
"""

import os, json, anthropic, httpx
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

# ── CONFIG ──────────────────────────────────────────────────────────────────
RECIPIENTS        = ["ir2511@columbia.edu"]
SENDER_EMAIL      = "onboarding@resend.dev"
SENDER_NAME       = "Première Intelligence"
PAGES_BASE_URL    = "https://ir2511-max.github.io/premiere-intelligence"
AUDIO_DIR         = "audio"

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
RESEND_API_KEY    = os.environ["RESEND_API_KEY"]
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY", "").strip()

HISTORY_FILE = "sent_history.json"
HISTORY_DAYS = 14

# ── HISTORY ──────────────────────────────────────────────────────────────────
def load_history() -> list:
    if not Path(HISTORY_FILE).exists():
        return []
    with open(HISTORY_FILE) as f:
        history = json.load(f)
    et = ZoneInfo("America/New_York")
    cutoff = datetime.now(et) - timedelta(days=HISTORY_DAYS)
    return [item for item in history if datetime.fromisoformat(item["sent_at"]) > cutoff]

def save_history(existing: list, new_stories: list, today_str: str):
    et = ZoneInfo("America/New_York")
    new_entries = [
        {"url": s["url"], "headline": s["headline"], "sent_at": datetime.now(et).isoformat(), "date": today_str}
        for s in new_stories if s.get("url", "").startswith("http")
    ]
    updated = existing + new_entries
    with open(HISTORY_FILE, "w") as f:
        json.dump(updated, f, indent=2)
    print(f"✓ History updated ({len(updated)} articles on record)")

# ── PROMPT ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are the editor of "Premiere Intelligence," a daily luxury-tech intelligence briefing for senior executives at LVMH. Your reader works in Media Data & Performance at a world-class luxury conglomerate.

Your job: surface EXACTLY 5 of the most signal-rich stories published in the past 7 days at the intersection of:
- AI + luxury fashion (LVMH, Kering, Richemont, Hermès, Prada, etc.)
- AI + media / advertising / performance marketing
- Media, data & tech shaping the luxury industry

CRITICAL RULES:
1. TIMELINESS IS THE HIGHEST PRIORITY.
Only include stories published within the last 7 days.
You MUST verify the publication date from the source before including any story.
When selecting between stories of similar relevance, always prefer the most recently published article.
Preference order:
- Published in the last 24 hours (highest priority)
- Published 2-3 days ago
- Published 4-5 days ago
- Published 6-7 days ago
A story published yesterday with slightly lower relevance should generally be preferred over a story published 6-7 days ago.
If you cannot confirm a publication date within the last 7 days, discard the story.
Do not present developments, announcements, reports, studies, product launches, or platform updates as breaking news if the underlying event first occurred several weeks earlier, even if the article itself was recently republished or recirculated.
2. Every story MUST have a real, working URL from a reputable, well-known publication. Acceptable sources include: major trade press (WWD, Business of Fashion, Vogue Business, Digiday, Adweek, Campaign, The Drum), leading business media (FT, WSJ, Bloomberg, Reuters, Forbes, Business Insider), top consultancies and research firms (McKinsey, Bain, BCG, Forrester, Gartner), and official company press releases on PR Newswire or BusinessWire. Do NOT use obscure blogs, low-authority websites, SEO content farms, or sources without clear editorial standards.
3. Write in a sharp, confident editorial voice — no fluff, no hedging.
4. Score each story 1–5 for relevance to a luxury media executive.
5. Assign each story one category from: MAISONS & BRANDS, CREATIVE & CAMPAIGNS, POLICY & RISK, COMMERCE & RETAIL, DATA & PERFORMANCE, MEDIA & PLATFORMS.
6. STRICT DEDUPLICATION: Before finalising your 5 stories, check every pair. If two stories cover the same underlying event, announcement, report, or deal — even from different publications — keep only ONE. Prefer the source that is FREE to access (no paywall). Only use a paywalled source if no free alternative covers the same story adequately. Paywalled sources include: Business of Fashion, WWD, Digiday (Digiday+), Campaign Live, MarketingProfs. Free sources include: Bain.com, PR Newswire, Digital Applied, Agile Brand Guide, Fashion Network, McKinsey, Adweek (partial), and most trade press. The final 5 must each cover a completely different news event.
7. Do NOT include any story from the EXCLUDED RECENT ARTICLES list provided by the user — these have already been covered in previous editions. This includes stories covering the SAME UNDERLYING TOPIC or REPORT, even if from a different source or with a different headline. For example, if the Bain luxury report, the Hermès AI index, or any other specific study has appeared in the exclusion list, do not cover it again under any framing or source.
8. FRESHNESS TEST:
For every story, determine:
- Publication date
- Number of days since publication

Stories older than 5 days should only be included when there is no stronger recent development available.

Your final selection should maximize both relevance AND recency.
9. The exclusion list applies not only to identical articles but also to the underlying event, announcement, study, report, product launch, platform update, or company news item. Do not re-cover the same news event from a different publication.


Return ONLY valid JSON, no markdown, no preamble:
{
  "date": "Day, D Month YYYY",
  "lede": "One sentence editorial summary of today's signal.",
  "stories": [
    {
      "category": "MAISONS & BRANDS",
      "score": 5,
      "headline": "Story headline here",
      "summary": "MAXIMUM 3 sentences. No more. Sharp and editorial.",
      "source": "Publication Name",
      "date": "D Month YYYY",
      "days_old": 1,
      "url": "https://real-article-url.com"
    }
  ]
}
  "stories": [
    {
      "category": "MAISONS & BRANDS",
      "score": 5,
      "headline": "Story headline here",
      "summary": "MAXIMUM 3 sentences. No more. Sharp and editorial.",
      "source": "Publication Name",
      "date": "D Month YYYY",
      "url": "https://real-article-url.com"
    }
  ]
}"""

# ── FETCH BRIEFING ────────────────────────────────────────────────────────────
def fetch_briefing(today_str: str, recent_articles: list) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    exclusion_block = ""
    if recent_articles:
        lines = "\n".join(
            f"- {a['headline']} | {a['url']} (sent {a['date']})"
            for a in recent_articles[-40:]
        )
        exclusion_block = f"\n\nEXCLUDED RECENT ARTICLES — do not include any of these:\n{lines}"

    messages = [{"role": "user", "content": (
        f"Today is {today_str}. Search for the 5 most important and MOST RECENT news stories published in the past 7 days. "
        f"Prioritize stories published in the last 72 hours whenever possible. "
        f"Avoid selecting stories that are 5-7 days old unless they are significantly more important than newer alternatives. "
        f"at the intersection of AI, luxury, media, and technology. "
        f"For each story, confirm its publication date before including it. "
        f"Return only verified, linkable stories in the JSON format specified."
        f"{exclusion_block}"
    )}]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        tools=[{"type": "web_search_20260318", "name": "web_search"}],
        system=SYSTEM_PROMPT,
        messages=messages
    )

    text = "".join(b.text for b in response.content if hasattr(b, "text") and b.type == "text")
    print(f"Response stop_reason: {response.stop_reason}, text length: {len(text)}")
    import re as _re
    # Try markdown code block first
    json_match = _re.search(r"```(?:json)?\s*(.*?)\s*```", text, _re.DOTALL)
    if json_match:
        clean = json_match.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        clean = text[start:end+1] if start != -1 and end != -1 else text.strip()
    if not clean:
        raise ValueError(f"Empty response. stop_reason={response.stop_reason}")
    # Fix common JSON issues: trailing commas
    clean = _re.sub(r",\s*}", "}", clean)
    clean = _re.sub(r",\s*]", "]", clean)
    return json.loads(clean)

# ── AUDIO ─────────────────────────────────────────────────────────────────────
def generate_audio_script(data: dict) -> str:
    stories_text = ""
    for i, s in enumerate(sorted(data["stories"], key=lambda x: -x["score"]), 1):
        stories_text += (
            f" Story {i}: {s['headline']}. "
            f"{s['summary']}"
        )
    return (
        f"Good morning. Today is {data['date']}. "
        f"Welcome to Première Intelligence, your daily luxury-tech briefing. "
        f"Here is today's signal: {data['lede']} "
        f"Here are your five stories for today."
        f"{stories_text} "
        f"That's your Première Intelligence briefing. Have a sharp day."
    )

def generate_audio(script: str, date_slug: str) -> str | None:
    key = OPENAI_API_KEY
    print(f"Audio key length: {len(key)}")
    if not key:
        print("No OPENAI_API_KEY — skipping audio")
        return None
    os.makedirs(AUDIO_DIR, exist_ok=True)
    # Clean up audio older than 14 days
    et = ZoneInfo("America/New_York")
    cutoff = datetime.now(et) - timedelta(days=14)
    for f in os.listdir(AUDIO_DIR):
        if f.endswith(".mp3"):
            try:
                fdate = datetime.strptime(f.replace(".mp3", ""), "%Y-%m-%d").replace(tzinfo=et)
                if fdate < cutoff:
                    os.remove(os.path.join(AUDIO_DIR, f))
                    print(f"✓ Removed old audio: {f}")
            except ValueError:
                pass
    # Truncate to OpenAI's 4096 char limit
    script = script[:4096]
    try:
        response = httpx.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "tts-1", "input": script, "voice": "nova"},
            timeout=60,
        )
        response.raise_for_status()
        filepath = f"{AUDIO_DIR}/{date_slug}.mp3"
        with open(filepath, "wb") as f:
            f.write(response.content)
        print(f"✓ Audio saved → {filepath}")
        return filepath
    except Exception as e:
        print(f"⚠ Audio generation failed: {e}")
        return None

# ── BUILD EMAIL HTML ──────────────────────────────────────────────────────────
def build_email(data: dict, audio_url: str | None = None) -> str:
    stories_html = ""
    for s in sorted(data["stories"], key=lambda x: -x["score"]):
        pips = "".join(
            f'<span style="display:inline-block;width:10px;height:4px;border-radius:1px;background:{"#b89a72" if i < s["score"] else "#ddd"};margin-right:2px;"></span>'
            for i in range(5)
        )
        read_link = f'<a href="{s["url"]}" style="font-size:10px;letter-spacing:0.1em;color:#b89a72;text-decoration:none;text-transform:uppercase;">Read →</a>' if s.get("url","").startswith("http") else ""
        stories_html += f"""
        <tr><td style="padding:28px 0;border-bottom:1px solid #e0d0c8;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:#7a6358;">{s["category"]}</span>
            <div>{pips}</div>
          </div>
          <h2 style="font-family:Georgia,serif;font-size:22px;font-weight:600;line-height:1.2;margin:0 0 10px;color:#1a1410;">{s["headline"]}</h2>
          <p style="font-size:13px;line-height:1.7;color:#3a2e28;margin:0 0 12px;">{s["summary"]}</p>
          <span style="font-size:10px;letter-spacing:0.08em;color:#7a6358;margin-right:16px;">{s["source"]}</span>
          <span style="font-size:10px;letter-spacing:0.08em;color:#b89a72;margin-right:16px;">{s.get("date","")}</span>
          {read_link}
        </td></tr>"""

    audio_button = ""
    if audio_url:
        audio_button = f"""
        <tr><td style="padding:16px 0 0;">
          <a href="{audio_url}" style="display:inline-block;font-size:10px;letter-spacing:0.15em;text-transform:uppercase;color:#1a1410;text-decoration:none;border:1px solid #1a1410;padding:8px 20px;">🎧 Listen to today's briefing</a>
        </td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5e6e0;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5e6e0;padding:40px 20px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr><td style="padding-bottom:6px;">
          <p style="font-size:9px;letter-spacing:0.18em;text-transform:uppercase;color:#7a6358;margin:0;">{data["date"]}</p>
        </td></tr>
        <tr><td style="border-bottom:2px solid #1a1410;padding-bottom:16px;">
          <table width="100%" cellpadding="0" cellspacing="0"><tr>
            <td>
              <div style="font-family:Georgia,serif;font-size:64px;font-weight:700;line-height:1;color:#1a1410;mso-line-height-rule:exactly;">PREMIÈRE</div>
              <div style="font-family:Georgia,serif;font-size:64px;font-weight:700;line-height:1;color:#1a1410;mso-line-height-rule:exactly;">INTELLIGENCE</div>
              <p style="font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:#7a6358;margin:10px 0 0;">The luxury-tech briefing</p>
            </td>
          </tr></table>
        </td></tr>

        <!-- Lede + audio button -->
        <tr><td style="border-bottom:1px solid #c9b5a8;padding:20px 0;">
          <p style="font-family:Georgia,serif;font-style:italic;font-size:16px;line-height:1.6;color:#1a1410;margin:0 0 16px;">{data["lede"]}</p>
          {audio_button}
        </td></tr>

        <!-- Stories -->
        {stories_html}

        <!-- Footer -->
        <tr><td style="padding-top:32px;text-align:center;">
          <p style="font-size:9px;letter-spacing:0.14em;text-transform:uppercase;color:#c9b5a8;margin:0;">
            Premiere Intelligence &nbsp;·&nbsp; The luxury-tech briefing &nbsp;·&nbsp; Delivered weekdays at 7:30 AM
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

# ── SEND EMAIL ────────────────────────────────────────────────────────────────
def send_email(subject: str, html: str):
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
        json={"from": f"{SENDER_NAME} <{SENDER_EMAIL}>", "to": RECIPIENTS, "subject": subject, "html": html},
        timeout=30,
    )
    response.raise_for_status()
    print(f"✓ Email sent → {RECIPIENTS}")
    return response.json()

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    et = ZoneInfo("America/New_York")
    raw_key = os.environ.get("OPENAI_API_KEY", "NOT_SET")
    print(f"OPENAI key status: len={len(raw_key)}, starts={raw_key[:7] if len(raw_key) > 7 else raw_key!r}")
    today_str  = datetime.now(et).strftime("%A, %d %B %Y")
    date_slug  = datetime.now(et).strftime("%Y-%m-%d")
    print(f"Fetching briefing for {today_str}…")

    recent_articles = load_history()
    print(f"Loaded {len(recent_articles)} recent articles to exclude.")

    # Retry once if JSON parsing fails
    data = None
    for attempt in range(2):
        try:
            data = fetch_briefing(today_str, recent_articles)
            break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt == 1:
                raise
            print("Retrying...")

    # Validate story freshness
    MAX_AGE_DAYS = 7

    validated_stories = []

    for story in data.get("stories", []):
        try:
            pub_date = datetime.strptime(
                story["date"],
                "%d %B %Y"
            )

            age_days = (datetime.now() - pub_date).days

            if age_days <= MAX_AGE_DAYS:
                validated_stories.append(story)
            else:
                print(
                    f"Removing old story: "
                    f"{story['headline']} ({age_days} days old)"
                )

        except Exception as e:
            print(
                f"Could not validate date for "
                f"{story.get('headline', 'Unknown')}: {e}"
            )

    data["stories"] = validated_stories

     if not data.get("stories"):
        print("No stories found today — skipping.")
        return


    # Generate audio
    # Audio is generated by a separate workflow (generate-audio.yml) to keep
    # this briefing independent of the OpenAI key. We still link the button to
    # where the audio WILL be, since the audio job runs right after this one.
    audio_url = f"{PAGES_BASE_URL}/audio/{date_slug}.html"

    # Persist today's briefing so the audio workflow can read it
    with open("latest_briefing.json", "w") as bf:
        json.dump({"date": data["date"], "lede": data["lede"],
                   "stories": data["stories"], "date_slug": date_slug}, bf, indent=2)
    print("✓ Wrote latest_briefing.json for audio workflow")

    html = build_email(data, audio_url)
    send_email(f"Premiere Intelligence — {today_str}", html)
    save_history(recent_articles, data["stories"], today_str)

if __name__ == "__main__":
    main()
