import os, zipfile, sqlite3, hashlib, time, shutil, requests
from lsm import config

# Make sure this points to your latest clean backup!
YUMA_BACKUP = "Yuma_PreUpdate_Backup.backup" 
EXTRACT_DIR = "yuma_injected"
DB_PATH = os.path.join(EXTRACT_DIR, "song.db")
OUT_BACKUP = "Yuma_Modified.backup"

LB_USERNAME = "lunatiuism" 

print(f"🌐 Fetching listening history for '{LB_USERNAME}'...")
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
            # Try to get the Cover Art Archive ID
            add_info = meta.get("additional_info", {})
            mbid = add_info.get("caa_release_mbid") or add_info.get("release_mbid")
            
            if mbid:
                thumb = f"https://coverartarchive.org/release/{mbid}/front-250"
            else:
                # Fallback if no album art exists in the database
                thumb = "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg" 
                
            all_listens.append({
                "listened_at": ts,
                "artist_name": meta.get("artist_name", "Unknown Artist"),
                "track_name": meta.get("track_name"),
                "thumb_url": thumb
            })
    max_ts = min(l["listened_at"] for l in listens) - 1
    print(f"   -> Fetched {len(all_listens)} tracks so far...")

print(f"✅ Total tracks fetched: {len(all_listens)}")
if not all_listens:
    exit(1)

# Deduplicate
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

print("💉 Injecting into SQLite with Real Album Art...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys=ON;")

now_ms = int(time.time() * 1000)
album_id = "lsm_global_album"
playlist_id = "lsm_playlist"

# Insert Album (giving it a generic icon so the album view doesn't crash)
album_thumb = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Music_note_nicu_buculei_01.svg/512px-Music_note_nicu_buculei_01.svg.png"
cursor.execute("""
    INSERT OR IGNORE INTO album (id, title, songCount, duration, explicit, lastUpdateTime, isLocal, thumbnailUrl) 
    VALUES (?, 'ListenBrainz Imports', 10000, 1800000000, 0, ?, 0, ?)
""", (album_id, now_ms, album_thumb))

# Insert Playlist
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
    real_thumb = item['thumb_url']
    
    hash_val = hashlib.md5(f"{artist_name} - {track_name}".encode()).hexdigest()
    song_id = hash_val[:11] 
    artist_hash = hashlib.md5(artist_name.encode()).hexdigest()
    artist_id = artist_hash[:24]
    
    # Insert Artist (using the track's thumb as the artist pic)
    cursor.execute("""
        INSERT OR IGNORE INTO artist (id, name, thumbnailUrl, channelId, lastUpdateTime, bookmarkedAt, blockedAt, isLocal) 
        VALUES (?, ?, ?, ?, ?, 0, NULL, 0)
    """, (artist_id, artist_name, real_thumb, artist_id, now_ms))
    
    # Insert Song (using real_thumb)
    cursor.execute("""
        INSERT OR IGNORE INTO song (id, title, duration, thumbnailUrl, albumId, albumName, explicit, year, date, dateModified, liked, likedDate, totalPlayTime, inLibrary, dateDownload, isLocal, isrc, likedYtm, likedSpotify) 
        VALUES (?, ?, ?, ?, ?, 'ListenBrainz Imports', 0, 2024, ?, ?, 0, 0, ?, 1, 0, 0, '', 0, 0)
    """, (song_id, track_name, play_ms, real_thumb, album_id, now_ms, now_ms, play_ms))
    
    cursor.execute("""
        INSERT OR IGNORE INTO song_artist_map (songId, artistId, position) 
        VALUES (?, ?, 0)
    """, (song_id, artist_id))
    
    cursor.execute("""
        INSERT OR IGNORE INTO song_album_map (songId, albumId, "index") 
        VALUES (?, ?, 0)
    """, (song_id, album_id))
    
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
            
print(f"🚀 Created {OUT_BACKUP} with real album art!")
