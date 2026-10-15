import pylast, requests, time, json, os
from . import config

STATE_FILE = ".lsm_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_sync_uts": 0}

def save_state(s):
    with open(STATE_FILE, "w") as f:
        json.dump(s, f)

def fetch_all(user, since_uts):
    listens = []
    time_to = None
    per_page = 200
    while True:
        try:
            tracks = user.get_recent_tracks(limit=per_page, time_to=time_to)
        except Exception as e:
            print(f"⚠  fetch error: {e}")
            break
        if not tracks:
            break
        stop = False
        for t in tracks:
            if not t.timestamp:
                continue
            ts = int(t.timestamp)
            if ts <= since_uts:
                stop = True
                break
            listens.append({
                "listened_at": ts,
                "track_metadata": {
                    "artist_name": t.track.artist.name,
                    "track_name": t.track.title,
                }
            })
        if stop or len(tracks) < per_page:
            break
        time_to = int(tracks[-1].timestamp) - 1
        time.sleep(0.5)
    return listens

def push(listens):
    if not listens:
        print("Nothing new to push.")
        return
    listens.sort(key=lambda x: x["listened_at"])
    batches = [listens[i:i+1000] for i in range(0, len(listens), 1000)]
    headers = {
        "Authorization": f"Token {config.LISTENBRAINZ_TOKEN}",
        "Content-Type": "application/json",
    }
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

def run():
    state = load_state()
    since = state.get("last_sync_uts", 0)
    print(f"📻 Syncing Last.fm → ListenBrainz (since {since})")
    net = pylast.LastFMNetwork(
        api_key=config.LASTFM_API_KEY,
        api_secret=config.LASTFM_API_SECRET,
        username=config.LASTFM_USERNAME,
    )
    user = net.get_user(config.LASTFM_USERNAME)
    listens = fetch_all(user, since)
    print(f"   found {len(listens)} new scrobbles")
    push(listens)
    if listens:
        state["last_sync_uts"] = max(l["listened_at"] for l in listens)
        save_state(state)
    print("✅ sync done")
