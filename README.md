# Listening Stats Merger (lsm)

A CLI tool to unify scattered music listening history into ListenBrainz.

## Install
```bash
git clone https://github.com/<your-username>/listening-stats-merger.git
cd listening-stats-merger
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configure
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

Required keys:
- `LASTFM_API_KEY` — https://www.last.fm/api/account/create
- `LASTFM_API_SECRET` — same page
- `LASTFM_USERNAME` — your Last.fm username
- `LISTENBRAINZ_TOKEN` — https://listenbrainz.org/settings/

## Usage
```bash
python -m lsm sync              # sync new Last.fm scrobbles
python -m lsm merge --pxpl file.pxpl
python -m lsm stats
```

## License
MIT
