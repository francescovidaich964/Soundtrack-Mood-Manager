#!/usr/bin/env python3
"""
get_refresh_token.py — one-time script to obtain a Spotify refresh token

Run this ONCE on any machine (Windows or Linux/macOS).
Pure Python stdlib — no extra installs needed.

What it does:
  1. Opens your browser to Spotify login.
  2. After login, Spotify redirects to /token.html on your GitHub Pages site.
     That page displays the full URL — you copy it and paste it here.
  3. The script exchanges the code for a refresh token and prints it.

Prerequisites:
  - config.json with client_id, client_secret, and github_pages_url filled in
  - webapp/token.html deployed to GitHub Pages (push to main first)
  - https://<you>.github.io/<repo>/token.html registered as a Redirect URI
    in your Spotify app (one-time setup)
"""

from __future__ import annotations

import base64
import json
import sys
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SCOPE     = "playlist-read-private"

# -----------------------------------------------------------------------
# Load credentials
# -----------------------------------------------------------------------

config_path = REPO_ROOT / "config.json"
if not config_path.exists():
    sys.exit(
        "ERROR: config.json not found.\n"
        "Copy config.json.example → config.json and fill in your credentials."
    )

with config_path.open(encoding="utf-8") as f:
    config = json.load(f)

CLIENT_ID     = config.get("client_id", "")
CLIENT_SECRET = config.get("client_secret", "")
pages_url     = config.get("github_pages_url", "").rstrip("/")

if not CLIENT_ID or not CLIENT_SECRET:
    sys.exit("ERROR: client_id and/or client_secret missing from config.json.")

if not pages_url:
    print("Enter your GitHub Pages URL (no trailing slash).")
    print("Example: https://francescovidaich964.github.io/Soundtrack-Mood-Manager")
    print()
    pages_url = input("GitHub Pages URL: ").strip().rstrip("/")

redirect_uri = pages_url + "/token.html"

# -----------------------------------------------------------------------
# Step 1 — Remind the user to register the redirect URI
# -----------------------------------------------------------------------

print()
print("Make sure this Redirect URI is added to your Spotify app:")
print()
print(f"  {redirect_uri}")
print()
print("  Spotify Dashboard → your app → Settings → Redirect URIs → Add → Save")
print()
input("Press Enter when ready...")

# -----------------------------------------------------------------------
# Step 2 — Open the browser to Spotify login
# -----------------------------------------------------------------------

auth_params = urllib.parse.urlencode({
    "response_type": "code",
    "client_id":     CLIENT_ID,
    "scope":         SCOPE,
    "redirect_uri":  redirect_uri,
})
auth_url = "https://accounts.spotify.com/authorize?" + auth_params

print()
print("Opening Spotify login in your browser...")
print("If it does not open automatically, visit this URL manually:")
print()
print(f"  {auth_url}")
print()

try:
    webbrowser.open(auth_url)
except Exception:
    pass

# -----------------------------------------------------------------------
# Step 3 — User copies the URL from token.html and pastes it here
# -----------------------------------------------------------------------

print("After logging in, your browser will land on a page titled")
print("'Soundtrack MoodPad — Token Setup' that shows a URL.")
print()
print("Click the URL box on that page, copy it (Ctrl+C), and paste it below.")
print()

redirected_url = input("Paste the full URL here: ").strip()

parsed = urllib.parse.urlparse(redirected_url)
params = urllib.parse.parse_qs(parsed.query)

if "error" in params:
    sys.exit(f"ERROR: Spotify returned an error: {params['error'][0]}")

if "code" not in params:
    sys.exit(
        "ERROR: No 'code=' parameter found in the URL.\n"
        "Make sure you copied the full URL from the token.html page."
    )

code = params["code"][0]

# -----------------------------------------------------------------------
# Step 4 — Exchange the code for a refresh token
# -----------------------------------------------------------------------

print()
print("Exchanging code for tokens...")

token_body = urllib.parse.urlencode({
    "grant_type":   "authorization_code",
    "code":         code,
    "redirect_uri": redirect_uri,
}).encode()

credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

req = urllib.request.Request(
    "https://accounts.spotify.com/api/token",
    data=token_body,
    headers={
        "Authorization": f"Basic {credentials}",
        "Content-Type":  "application/x-www-form-urlencoded",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req) as resp:
        token_data = json.loads(resp.read())
except urllib.error.HTTPError as e:
    body = e.read().decode()
    sys.exit(f"ERROR: Token exchange failed ({e.code}): {body}")

refresh_token = token_data.get("refresh_token")
if not refresh_token:
    sys.exit("ERROR: No refresh_token in response. Something went wrong.")

# -----------------------------------------------------------------------
# Step 5 — Print the result
# -----------------------------------------------------------------------

print()
print("=" * 60)
print("SUCCESS! Your Spotify refresh token:")
print("=" * 60)
print(refresh_token)
print("=" * 60)
print()
print("Next steps:")
print("  1. Go to your GitHub repo → Settings → Secrets and variables")
print("     → Actions → New repository secret")
print("  2. Name:  SPOTIFY_REFRESH_TOKEN")
print("  3. Value: (the token printed above)")
print()
print("After that, re-run the Sync Playlist workflow.")
