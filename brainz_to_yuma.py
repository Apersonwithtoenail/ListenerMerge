import os, zipfile, sqlite3, hashlib, time, shutil, requests
from lsm import config

YUMA_BACKUP = "Yuma_20261017144531.backup"
EXTRACT_DIR = "yuma_injected"
DB_PATH = os.path.join(EXTRACT_DIR, "song.db")
OUT_BACKUP = "Yuma_Modified.backup"

LB_USERNAME = "lunatiuism" 

print(f"🌐 Fetching listening history for '{LB_USERNAME}' from ListenBrainz API...")
headers = {"Authorization": f"Token {config.LISTENBRAINZ_TOKEN}"}

all_listens = []
max_ts = int(time.time())
while True:
    url = f"https://api.listenbrainz.org/1/user/{LB_USERNAME}/listens?count=1000&max_ts={max_ts}"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"❌ Error: {r.text}")
        break
    data = r.json()
    listens = data.get("payload", {}).get("listens", [])
    if not listens:
        break
    for l in listens:
        ts = l.get("listened_at")
        meta = l.get("track_metadata", {})
        if ts and meta.get("track_name"):
            all_listens.append({
                "listened_at": ts,
                "artist_name": meta.get("artist_name", "Unknown Artist"),
                "track_name": meta.get("track_name")
            })
    max_ts = min(l["listened_at"] for l in listens) - 1
    print(f"   -> Fetched {len(all_listens)} tracks so far...")

print(f"✅ Total tracks fetched: {len(all_listens)}")
if not all_listens:
    exit(1)

unique_listens = {}
for l in all_listens:
    key = (l['artist_name'], l['track_name'], l['listened_at'])
    unique_listens[key] = l
listens_to_inject = sorted(unique_listens.values(), key=lambda x: x['listened_at'])

print("📦 Extracting fresh Yuma backup...")
if os.path.exists(EXTRACT_DIR):
    shutil.rmtree(EXTRACT_DIR)
os.makedirs(EXTRACT_DIR)
with zipfile.ZipFile(YUMA_BACKUP, 'r') as z:
    z.extractall(EXTRACT_DIR)

print("💉 Injecting into SQLite with Playlists...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys=ON;")

now_ms = int(time.time() * 1000)
album_id = "lsm_global_album"
playlist_id = "lsm_playlist"
thumb_url = "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"

# 1. Insert Album
cursor.execute("""
    INSERT OR IGNORE INTO album (id, title, songCount, duration, explicit, lastUpdateTime, isLocal) 
    VALUES (?, 'Unknown Album', 10000, 1800000000, 0, ?, 0)
""", (album_id, now_ms))

# 2. Insert Playlist
cursor.execute("""
    INSERT OR IGNORE INTO playlist (id, name, createdAt, lastUpdateTime, isEditable, bookmarkedAt, isLocal, isAutoSync, remoteSongCount) 
    VALUES (?, 'ListenBrainz Import', ?, ?, 1, ?, 0, 0, ?)
""", (playlist_id, now_ms, now_ms, now_ms, len(listens_to_inject)))

injected = 0
for item in listens_to_inject:
    artist_name = item['artist_name']
    track_name = item['track_name']
    ts_ms = item['listened_at'] * 1000
    play_ms = 180000 
    
    hash_val = hashlib.md5(f"{artist_name} - {track_name}".encode()).hexdigest()
    song_id = hash_val[:11] 
    artist_hash = hashlib.md5(artist_name.encode()).hexdigest()
    artist_id = artist_hash[:24]
    
    cursor.execute("""
        INSERT OR IGNORE INTO artist (id, name, thumbnailUrl, channelId, lastUpdateTime, bookmarkedAt, blockedAt, isLocal) 
        VALUES (?, ?, ?, ?, ?, 0, 0, 0)
    """, (artist_id, artist_name, thumb_url, artist_id, now_ms))
    
    cursor.execute("""
        INSERT OR IGNORE INTO song (id, title, duration, thumbnailUrl, albumId, albumName, explicit, year, date, dateModified, liked, likedDate, totalPlayTime, inLibrary, dateDownload, isLocal, isrc, likedYtm, likedSpotify) 
        VALUES (?, ?, ?, ?, ?, 'Unknown Album', 0, 2024, ?, ?, 0, 0, ?, 1, 0, 0, '', 0, 0)
    """, (song_id, track_name, play_ms, thumb_url, album_id, now_ms, now_ms, play_ms))
    
    cursor.execute("""
        INSERT OR IGNORE INTO song_artist_map (songId, artistId, position) 
        VALUES (?, ?, 0)
    """, (song_id, artist_id))
    
    cursor.execute("""
        INSERT OR IGNORE INTO song_album_map (songId, albumId, "index") 
        VALUES (?, ?, 0)
    """, (song_id, album_id))
    
    # Map to playlist
    cursor.execute("""
        INSERT OR IGNORE INTO playlist_song_map (playlistId, songId, position, setVideoId) 
        VALUES (?, ?, ?, 'lsm_vid')
    """, (playlist_id, song_id, injected))
    
    cursor.execute("""
        INSERT INTO event (songId, timestamp, playTime) 
        VALUES (?, ?, ?)
    """, (song_id, ts_ms, play_ms))
    injected += 1

print("🔄 Rebuilding playCount cache...")
cursor.execute("DELETE FROM playCount;")
cursor.execute("""
    INSERT INTO playCount (song, year, month, count)
    SELECT 
        songId, 
        CAST(strftime('%Y', datetime(timestamp/1000, 'unixepoch')) AS INTEGER) as y,
        CAST(strftime('%m', datetime(timestamp/1000, 'unixepoch')) AS INTEGER) as m,
        COUNT(*)
    FROM event
    GROUP BY songId, y, m;
""")

conn.commit()
cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
conn.close()

for ext in ["-wal", "-shm"]:
    p = os.path.join(EXTRACT_DIR, f"song.db{ext}")
    if os.path.exists(p):
        os.remove(p)

with zipfile.ZipFile(OUT_BACKUP, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(EXTRACT_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, EXTRACT_DIR)
            z.write(file_path, arcname)
            
print(f"🚀 Created {OUT_BACKUP} with {injected} events + playlist.")
