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
HISTORY_DAYS = 7

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

Your job: surface EXACTLY 5 of the most signal-rich stories published VERY RECENTLY at the intersection of:
- AI + luxury fashion (LVMH, Kering, Richemont, Hermès, Prada, etc.)
- AI + media / advertising / performance marketing
- Media, data & tech shaping the luxury industry

CRITICAL RULES:
1. TIMELINESS IS THE #1 PRIORITY. Before including any story, you MUST open the article or search result and confirm the exact publication date. Stories must be published within the last 3 days. If you cannot find an article from the last 3 days on a topic, look harder — do not fall back to older articles. If truly nothing fresh exists on a topic, pick a different topic. Prioritise stories from TODAY and YESTERDAY above all else. Never include a story where you are unsure of the date.
2. Every story MUST have a real, working URL from a reputable, well-known publication. Acceptable sources include: major trade press (WWD, Business of Fashion, Vogue Business, Digiday, Adweek, Campaign, The Drum), leading business media (FT, WSJ, Bloomberg, Reuters, Forbes, Business Insider), top consultancies and research firms (McKinsey, Bain, BCG, Forrester, Gartner), and official company press releases on PR Newswire or BusinessWire. Do NOT use obscure blogs, low-authority websites, SEO content farms, or sources without clear editorial standards.
3. Write in a sharp, confident editorial voice — no fluff, no hedging.
4. Score each story 1–5 for relevance to a luxury media executive.
5. Assign each story one category from: MAISONS & BRANDS, CREATIVE & CAMPAIGNS, POLICY & RISK, COMMERCE & RETAIL, DATA & PERFORMANCE, MEDIA & PLATFORMS.
6. STRICT DEDUPLICATION: Before finalising your 5 stories, check every pair. If two stories cover the same underlying event, announcement, report, or deal — even from different publications — keep only ONE. Prefer the source that is FREE to access (no paywall). The final 5 must each cover a completely different news event.
7. Do NOT include any story from the RECENT TOPICS list provided by the user — these have already been covered in previous editions. This includes stories covering the SAME UNDERLYING TOPIC or REPORT, even if from a different source or with a different headline.
8. MAXIMUM 3 sentences per summary. No more. Sharp and editorial.

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
      "url": "https://real-article-url.com"
    }
  ]
}"""

# ── FETCH BRIEFING ────────────────────────────────────────────────────────────
def fetch_briefing(today_str: str, recent_articles: list) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    exclusion_block = ""
    if recent_articles:
        def extract_topic(headline):
            return " ".join(headline.split()[:6])
        lines = "\n".join(
            f"- {extract_topic(a['headline'])} ({a['date']})"
            for a in recent_articles[-20:]
        )
        exclusion_block = f"\n\nRECENT TOPICS ALREADY COVERED — do not cover these again:\n{lines}"

    messages = [{"role": "user", "content": (
        f"Today is {today_str}. Search for the 5 most important news stories published in the last 3 days "
        f"at the intersection of AI, luxury, media, and technology. "
        f"You MUST verify the exact publication date of each article before including it — if it is older than 3 days, skip it. "
        f"Prioritise stories from today and yesterday. "
        f"Return only verified, linkable stories in the JSON format specified."
        f"{exclusion_block}"
    )}]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=16000,
        tools=[{"type": "web_search_20260318", "name": "web_search"}],
        system=SYSTEM_PROMPT,
        messages=messages
    )

    text = "".join(b.text for b in response.content if hasattr(b, "text") and b.type == "text")
    print(f"Response stop_reason: {response.stop_reason}, text length: {len(text)}")
    import re as _re
    json_match = _re.search(r"```(?:json)?\s*(.*?)\s*```", text, _re.DOTALL)
    if json_match:
        clean = json_match.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        clean = text[start:end+1] if start != -1 and end != -1 else text.strip()
    if not clean:
        raise ValueError(f"Empty response. stop_reason={response.stop_reason}")
    clean = _re.sub(r",\s*}", "}", clean)
    clean = _re.sub(r",\s*]", "]", clean)
    return json.loads(clean)

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
        <tr><td style="border-bottom:1px solid #c9b5a8;padding:20px 0;">
          <p style="font-family:Georgia,serif;font-style:italic;font-size:16px;line-height:1.6;color:#1a1410;margin:0 0 16px;">{data["lede"]}</p>
          {audio_button}
        </td></tr>
        {stories_html}
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
    today_str  = datetime.now(et).strftime("%A, %d %B %Y")
    date_slug  = datetime.now(et).strftime("%Y-%m-%d")
    print(f"Fetching briefing for {today_str}…")

    recent_articles = load_history()
    print(f"Loaded {len(recent_articles)} recent articles to exclude.")

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

    if not data.get("stories"):
        print("No stories found today — skipping.")
        return

    print(f"Found {len(data['stories'])} stories.")

    audio_url = f"{PAGES_BASE_URL}/audio/{date_slug}.html"

    with open("latest_briefing.json", "w") as bf:
        json.dump({"date": data["date"], "lede": data["lede"],
                   "stories": data["stories"], "date_slug": date_slug}, bf, indent=2)
    print("✓ Wrote latest_briefing.json for audio workflow")

    html = build_email(data, audio_url)
    send_email(f"Premiere Intelligence — {today_str}", html)
    save_history(recent_articles, data["stories"], today_str)

if __name__ == "__main__":
    main()
