import os, io, glob, json, zipfile
import requests, time
from dateutil import parser as dp
from bs4 import BeautifulSoup
from . import config

def parse_spotify(folder):
    out = []
    for fp in glob.glob(os.path.join(folder, "Streaming_History_Audio_*.json")):
        with open(fp, encoding="utf-8") as f:
            for item in json.load(f):
                if not item.get("master_metadata_track_name"):
                    continue
                ts = int(dp.isoparse(item["ts"]).timestamp())
                out.append({
                    "listened_at": ts,
                    "track_metadata": {
                        "artist_name": item.get("master_metadata_album_artist_name", "Unknown"),
                        "track_name": item["master_metadata_track_name"],
                        "release_name": item.get("master_metadata_album_album_name", ""),
                    }
                })
    return out

def parse_youtube(folder):
    html = os.path.join(folder, "YouTube and YouTube Music", "history", "watch-history.html")
    if not os.path.exists(html):
        return []
    out = []
    with open(html, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    for cell in soup.select("div.outer-cell"):
        cap = cell.select_one("div.mdl-typography--caption")
        if cap and "From Google Ads" in cap.get_text():
            continue
        c = cell.select_one("div.content-cell")
        if not c:
            continue
        parts = [t.strip() for t in c.strings if t.strip()]
        if not parts or parts[0] != "Watched":
            continue
        links = c.find_all("a")
        if not links:
            continue
        track = links[0].get_text().strip()
        artist = links[1].get_text().strip() if len(links) > 1 else "Unknown"
        try:
            ts = int(dp.parse(parts[-1]).timestamp())
        except Exception:
            continue
        out.append({
            "listened_at": ts,
            "track_metadata": {"artist_name": artist, "track_name": track}
        })
    return out

def parse_pxpl(path):
    with open(path, "rb") as f:
        data = f.read()
    idx = data.find(b"PK\x03\x04")
    if idx < 0:
        return []
    with zipfile.ZipFile(io.BytesIO(data[idx:])) as z:
        with z.open("playback_history.json") as f:
            items = json.load(f)
    out = []
    for it in items:
        ts = it.get("timestamp", 0)
        if ts > 9999999999:
            ts //= 1000
        if not ts or not it.get("title"):
            continue
        out.append({
            "listened_at": int(ts),
            "track_metadata": {
                "artist_name": it.get("artist") or "Unknown",
                "track_name": it["title"]
            }
        })
    return out

def push(listens):
    if not listens:
        print("Nothing to push.")
        return
    listens.sort(key=lambda x: x["listened_at"])
    headers = {
        "Authorization": f"Token {config.LISTENBRAINZ_TOKEN}",
        "Content-Type": "application/json",
    }
    batches = [listens[i:i+1000] for i in range(0, len(listens), 1000)]
    for i, b in enumerate(batches, 1):
        r = requests.post(
            config.LB_API_URL,
            headers=headers,
            json={"listen_type": "import", "payload": b},
        )
        if r.status_code == 200:
            print(f"   ✅ batch {i}/{len(batches)}")
        else:
            print(f"   ❌ batch {i}: {r.status_code} {r.text[:120]}")
            return
        time.sleep(1)

def run(spotify_dir, takeout_dir, pxpl):
    print("🎵 Merging local sources...")
    all_l = []
    if os.path.isdir(spotify_dir):
        s = parse_spotify(spotify_dir)
        print(f"   Spotify: {len(s)}")
        all_l += s
    if os.path.isdir(takeout_dir):
        y = parse_youtube(takeout_dir)
        print(f"   YouTube: {len(y)}")
        all_l += y
    if pxpl and os.path.exists(pxpl):
        p = parse_pxpl(pxpl)
        print(f"   PixelMusic: {len(p)}")
        all_l += p
    print(f"📊 total: {len(all_l)}")
    push(all_l)
    print("✅ merge done")
