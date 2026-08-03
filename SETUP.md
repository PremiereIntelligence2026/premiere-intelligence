# Isabella's Alerts — Setup Guide
### From zero to inbox in ~20 minutes

---

## What you'll have when done
- A beautiful landing page (like the one your friend built) hosted free on GitHub
- An automated email sent to you + your boss every weekday at 7:30 AM
- Real verified news only — no hallucinated stories

---

## Step 1 — Create a GitHub account (5 min)
1. Go to **github.com** and sign up (free)
2. Verify your email

---

## Step 2 — Create your repository (3 min)
1. Click the **+** icon (top right) → **New repository**
2. Name it: `isabellas-alerts`
3. Set to **Public**
4. Click **Create repository**
5. Upload all 3 files from this folder:
   - `index.html`
   - `send_briefing.py`
   - `.github/workflows/daily-briefing.yml`

   *(Drag and drop them into the GitHub file upload screen)*

---

## Step 3 — Enable GitHub Pages (landing page) (2 min)
1. In your repo → **Settings** → **Pages**
2. Under "Source" select **Deploy from a branch**
3. Branch: **main** / Folder: **/ (root)**
4. Click **Save**
5. Your site will be live at: `https://YOUR-USERNAME.github.io/isabellas-alerts`

---

## Step 4 — Set up Resend (email sending) (5 min)
1. Go to **resend.com** → Sign up free
2. Go to **Domains** → Add your email domain (or use their free @resend.dev address for testing)
3. Go to **API Keys** → Create a new key → Copy it

---

## Step 5 — Edit the Python script (2 min)
Open `send_briefing.py` and edit these two lines:
```python
RECIPIENTS   = ["your@email.com", "boss@email.com"]   # ← your emails
SENDER_EMAIL = "alerts@yourdomain.com"                 # ← your verified Resend sender
```

---

## Step 6 — Add your secret API keys to GitHub (3 min)
1. In your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** and add:

| Name | Value |
|------|-------|
| `ANTHROPIC_API_KEY` | Your key from console.anthropic.com |
| `RESEND_API_KEY` | Your key from resend.com |

---

## Step 7 — Test it! (1 min)
1. Go to your repo → **Actions** tab
2. Click **Isabella's Alerts — Daily Briefing**
3. Click **Run workflow** → **Run workflow**
4. Watch it run — check your inbox in ~2 minutes ✓

---

## Schedule
The email runs automatically every **Monday–Friday at 7:30 AM ET**.
No action needed — it just works.

> **Note:** GitHub Actions uses UTC. The cron `30 11 * * 1-5` = 7:30 AM ET (summer/EDT).
> In winter (EST, UTC-5), change to `30 12 * * 1-5`.

---

## Troubleshooting
- **Email not arriving?** Check Actions tab for error logs
- **API key error?** Make sure you copied the full key (starts with `sk-ant-`)
- **Resend error?** Make sure your sender domain is verified in Resend dashboard
