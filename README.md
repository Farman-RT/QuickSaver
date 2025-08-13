# QuicSaver — Fast Video Downloader

Tools used: **VS Code, HTML/CSS/JS, Python (Flask), yt-dlp, ffmpeg**. No other tools.

## 1) Local Run (Windows 10 Pro)

```bat
cd QuickSaver_ready
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
set FLASK_DEBUG=1
python app.py
```
Open: http://127.0.0.1:5000

### Notes
- If downloads are slow/fail on local, it’s usually **network DNS/ISP throttling**. The server code already uses:
  - `--extractor-args youtube:player_client=android`
  - `-N 4` fragment concurrency
  - MP4 preference for compatibility
- Files stream to the browser and are **deleted** from server afterward.
- Admin page only shows **URL logs count** (no user data storage). Change `ADMIN_PASSWORD` in `config.py`.

## 2) PropellerAds / AdSense Integration (5s Ad Gate)
- Insert your ad tag script **inside**:
  - `templates/home.html` → inside `<div class="gate-ad">...</div>` for the 5s gate
  - `templates/base.html` footer ads (3 blocks)
  - `templates/home.html` top left/right ads
  - `templates/earn.html` 10-grid ads
- Search these comments and replace with your real code:
  - `<!-- ADS PLACEHOLDER:`
  - `<!-- PropellerAds tag placeholder:`

## 3) 5-Second Gate (Same Tab)
- User clicks **Download** → backend prepares file (`/api/download`) → 5s modal appears with ad → **Continue** → same-tab download from `/download/<token>`.
- No new tab opens.

## 4) Deploy to Render.com

**Create repo:**
1. Put these files in a folder (this project).
2. Commit & push to GitHub.

**Render steps:**
1. New → Web Service → Connect your repo.
2. Runtime: Python
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python app.py`
5. Add env vars:
   - `FLASK_DEBUG=0`
   - `HOST=0.0.0.0`
   - `PORT=10000`
6. Deploy.

Render provides a public URL. Test with a YouTube/Facebook/Instagram link.

## 5) SEO (US + Global)
- Fast, responsive, semantic HTML. Titles & meta description added.
- Add your analytics + sitemap later if needed.

## 6) Where to Edit Ad Codes Later
- `templates/home.html` (2 top + gate modal)
- `templates/base.html` footer 3 ads
- `templates/earn.html` 10 ads
(Find the placeholders and paste provider’s tags.)

## 7) Troubleshooting
- **Only .part file?** That happens if the process is interrupted. Our code waits for completion and only serves the final file. If you still see issues on local, check your network.
- **YouTube Shorts failing:** Already mitigated with `--extractor-args youtube:player_client=android`. Try a different link or retry.
- **Big files memory?** The server streams in chunks; it does not buffer whole file.

## 8) Security
- `/download/<token>` serves files only from `tmp/` and deletes them after streaming.
- Admin page requires password.

## 9) Change Site Name/Branding
- Edit `templates/base.html` and `/static/img/favicon.ico`.
