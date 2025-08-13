import os
import sqlite3
import time
import uuid
import mimetypes
import subprocess
from flask import Flask, render_template, request, Response, g, jsonify
from werkzeug.utils import secure_filename
import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(BASE_DIR, "tmp")
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "urls.db")

os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)

# ---------- SQLite helpers ----------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute(
        "CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT, timestamp INTEGER)"
    )
    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

with app.app_context():
    init_db()

# ---------- Routes ----------
@app.route("/")
def home():
    return render_template("home.html", title="QuicSaver - Fast Video Downloader")

@app.route("/adsense")
def adsense():
    return render_template("adsense.html", title="QuicSaver - Ads Preview")

@app.route("/earn")
def earn():
    return render_template("earn.html", title="Earn - QuicSaver")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    msg = ""
    rows = None
    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw == config.ADMIN_PASSWORD:
            db = get_db()
            cur = db.execute("SELECT * FROM urls ORDER BY timestamp DESC LIMIT 200")
            rows = cur.fetchall()
        else:
            msg = "Wrong password"
    return render_template("admin.html", rows=rows, msg=msg, title="Admin - QuicSaver")

def stream_file_and_delete(path):
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 256)
                if not chunk:
                    break
                yield chunk
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

@app.route("/api/download", methods=["POST"])
def api_download():
    """AJAX endpoint: returns a JSON with a token if file is ready; 
    then front-end triggers a streamed download from /download/<token> in SAME TAB after 5s ad gate.
    """
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    fmt = (data.get("format") or "mp4").strip().lower()

    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return jsonify({"ok": False, "error": "Invalid URL"}), 400

    # Save URL to DB for admin stats
    try:
        db = get_db()
        db.execute("INSERT INTO urls (url,timestamp) VALUES (?,?)", (url, int(time.time())))
        db.commit()
    except Exception as e:
        app.logger.error("DB insert error: %s", e)

    uid = uuid.uuid4().hex[:10]
    out_template = os.path.join(TMP_DIR, f"video-{uid}.%(ext)s")

    # yt-dlp args tuned for speed & Shorts SABR workaround
    args = ["yt-dlp",
            "--no-playlist",
            "--geo-bypass",
            "-N", "4",  # fragments concurrency
            "--extractor-args", "youtube:player_client=android",  # avoid SABR in many cases
            "-o", out_template]

    if fmt == "mp3":
        args += ["-x", "--audio-format", "mp3"]
        # Prefer m4a when possible for speed/quality
        args += ["-S", "abr,asr,ext:m4a"]
    else:
        # Prefer mp4 container for best compatibility
        # Fallback to best if mp4 not available
        args += ["-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"]
        args += ["-S", "res,ext:mp4:m4a"]

    args.append(url)

    app.logger.info("Running yt-dlp: %s", " ".join(args))
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60*12)
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "Download timed out"}), 504
    except Exception as e:
        app.logger.error("yt-dlp run error: %s", e)
        return jsonify({"ok": False, "error": "Server process error"}), 500

    # Look for final file (avoid .part)
    found = None
    for f in os.listdir(TMP_DIR):
        if f.startswith("video-" + uid) and not f.endswith(".part"):
            found = os.path.join(TMP_DIR, f)
            break

    if not found or not os.path.exists(found):
        app.logger.error("Download failed. stdout: %s stderr: %s",
                         proc.stdout.decode('utf-8', errors='ignore'),
                         proc.stderr.decode('utf-8', errors='ignore'))
        return jsonify({"ok": False, "error": "Failed to download. Try a different link."}), 500

    token = os.path.basename(found)
    return jsonify({"ok": True, "token": token})

@app.route("/download/<path:token>")
def direct_download(token):
    # Security: restrict to our tmp folder files only
    safe_name = os.path.basename(token)
    path = os.path.join(TMP_DIR, safe_name)
    if not os.path.isfile(path):
        return "File not found or expired", 404

    mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    file_size = os.path.getsize(path)

    headers = {
        "Content-Disposition": f'attachment; filename="{safe_name}"',
        "Content-Type": mime_type,
        "Content-Length": str(file_size)
    }
    return Response(stream_file_and_delete(path), headers=headers)

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    # For Render.com, PORT is provided via env variable
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
