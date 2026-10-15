import os
from dotenv import load_dotenv

load_dotenv()

LASTFM_API_KEY     = os.getenv("LASTFM_API_KEY")
LASTFM_API_SECRET  = os.getenv("LASTFM_API_SECRET")
LASTFM_USERNAME    = os.getenv("LASTFM_USERNAME")
LISTENBRAINZ_TOKEN = os.getenv("LISTENBRAINZ_TOKEN")

LB_API_URL = "https://api.listenbrainz.org/1/submit-listens"

def check():
    missing = [k for k, v in {
        "LASTFM_API_KEY": LASTFM_API_KEY,
        "LASTFM_API_SECRET": LASTFM_API_SECRET,
        "LASTFM_USERNAME": LASTFM_USERNAME,
        "LISTENBRAINZ_TOKEN": LISTENBRAINZ_TOKEN,
    }.items() if not v]
    if missing:
        print(f"❌ Missing in .env: {', '.join(missing)}")
        return False
    return True
