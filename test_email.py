#!/usr/bin/env python3
"""
Test script — sends a sample email with audio button.
No Anthropic API call. Zero AI credits used.
"""
import os, httpx

RESEND_API_KEY  = os.environ["RESEND_API_KEY"]
OPENAI_API_KEY  = os.environ.get("OPENAI_API_KEY", "").strip()
RECIPIENT       = "ir2511@columbia.edu"
PAGES_BASE_URL  = "https://ir2511-max.github.io/premiere-intelligence"
DATE_SLUG       = "test"

# ── Fake data ────────────────────────────────────────────────────────────────
data = {
    "date": "Wednesday, 24 June 2026",
    "lede": "This is a test edition to confirm the audio button is working correctly.",
    "stories": [
        {
            "category": "MEDIA & PLATFORMS",
            "score": 5,
            "headline": "Test Story — Audio Button Check",
            "summary": "This is a test story to verify the email layout and audio button are rendering correctly before tomorrow's live run.",
            "source": "Première Intelligence",
            "date": "24 June 2026",
            "url": "https://ir2511-max.github.io/premiere-intelligence"
        }
    ]
}

# ── Generate audio ────────────────────────────────────────────────────────────
audio_url = None
if OPENAI_API_KEY:
    print("Generating audio...")
    r = httpx.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={"model": "tts-1", "input": "Bonjour. Ceci est un test de Première Intelligence. L'audio fonctionne correctement.", "voice": "nova"},
        timeout=30,
    )
    if r.status_code == 200:
        os.makedirs("audio", exist_ok=True)
        with open(f"audio/{DATE_SLUG}.mp3", "wb") as f:
            f.write(r.content)
        audio_url = f"{PAGES_BASE_URL}/audio/{DATE_SLUG}.mp3"
        print(f"✓ Audio saved")
    else:
        print(f"⚠ Audio failed: {r.text}")

# ── Build email ───────────────────────────────────────────────────────────────
audio_button = ""
if audio_url:
    audio_button = f"""
    <tr><td style="padding:16px 0 0;">
      <a href="{audio_url}" style="display:inline-block;font-size:10px;letter-spacing:0.15em;text-transform:uppercase;color:#1a1410;text-decoration:none;border:1px solid #1a1410;padding:8px 20px;">🎧 Listen to today's briefing</a>
    </td></tr>"""

s = data["stories"][0]
html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5e6e0;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5e6e0;padding:40px 20px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
        <tr><td style="padding-bottom:6px;">
          <p style="font-size:9px;letter-spacing:0.18em;text-transform:uppercase;color:#7a6358;margin:0;">{data["date"]}</p>
        </td></tr>
        <tr><td style="border-bottom:2px solid #1a1410;padding-bottom:16px;">
          <h1 style="font-family:Georgia,serif;font-size:72px;font-weight:700;line-height:0.88;margin:0;color:#1a1410;">PREMIÈRE<br>INTELLIGENCE</h1>
          <p style="font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:#7a6358;margin:10px 0 0;">The luxury-tech briefing</p>
        </td></tr>
        <tr><td style="border-bottom:1px solid #c9b5a8;padding:20px 0;">
          <p style="font-family:Georgia,serif;font-style:italic;font-size:16px;line-height:1.6;color:#1a1410;margin:0 0 16px;">{data["lede"]}</p>
          {audio_button}
        </td></tr>
        <tr><td style="padding:28px 0;">
          <span style="font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:#7a6358;">{s["category"]}</span>
          <h2 style="font-family:Georgia,serif;font-size:22px;font-weight:600;line-height:1.2;margin:8px 0 10px;color:#1a1410;">{s["headline"]}</h2>
          <p style="font-size:13px;line-height:1.7;color:#3a2e28;margin:0 0 12px;">{s["summary"]}</p>
          <span style="font-size:10px;color:#7a6358;">{s["source"]}</span>
          <span style="font-size:10px;color:#b89a72;margin-left:16px;">{s["date"]}</span>
        </td></tr>
        <tr><td style="padding-top:32px;text-align:center;">
          <p style="font-size:9px;letter-spacing:0.14em;text-transform:uppercase;color:#c9b5a8;margin:0;">
            Premiere Intelligence &nbsp;·&nbsp; Audio button test
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

# ── Send email ────────────────────────────────────────────────────────────────
r = httpx.post(
    "https://api.resend.com/emails",
    headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
    json={"from": "Première Intelligence <onboarding@resend.dev>", "to": [RECIPIENT], "subject": "TEST — Audio Button Check", "html": html},
    timeout=30,
)
r.raise_for_status()
print(f"✓ Test email sent to {RECIPIENT}")
