# Listenermerge

**CLI to unify your music listening history into [ListenBrainz](https://listenbrainz.org).**

Pulls scrobbles from Last.fm and imports local backups from Spotify, YouTube Music, and Pixel Music — then pushes everything to one ListenBrainz profile.

## Why

Your listening history is scattered across:

- **Last.fm** — live scrobbles from any player
- **Spotify** — Extended Streaming History (JSON)
- **YouTube Music** — Takeout watch-history (HTML)
- **Pixel Music** — `.pxpl` backup archives

Listenermerge merges all of them into your ListenBrainz account, so your stats are in one place.

## Features

- `sync` — incremental Last.fm → ListenBrainz (only new scrobbles)
- `merge` — bulk import from Spotify / YT Music / Pixel Music backups
- `stats` — shows last sync time
- State file so re-runs don't duplicate scrobbles
- Strips noise from track titles (feat., remaster, official video)
- Pure Python — no external API keys beyond Last.fm + ListenBrainz

## Requirements

- Python 3.10+
- Last.fm API key + secret — [create one](https://www.last.fm/api/account/create)
- ListenBrainz user token — [get it](https://listenbrainz.org/settings/)

## Install

    git clone https://github.com/Apersonwithtoenail/Listenermerge.git
    cd Listenermerge
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

## Configure

Copy the example and fill in your keys:

    cp .env.example .env
    gedit .env

Edit these four lines:

    LASTFM_API_KEY=your_key
    LASTFM_API_SECRET=your_secret
    LASTFM_USERNAME=your_lastfm_username
    LISTENBRAINZ_TOKEN=your_token

**Never commit `.env`.** It is gitignored.

## Usage

### Sync new Last.fm scrobbles

    python -m lsm sync

Fetches new scrobbles since last run, pushes them to ListenBrainz. Safe to run repeatedly.

### Merge local backups

    python -m lsm merge --spotify /path/to/spotify/json \
                        --takeout /path/to/takeout/ \
                        --pxpl /path/to/file.pxpl

- `--spotify` — folder containing Spotify Extended Streaming History JSON files
- `--takeout` — folder containing YouTube Music `watch-history.html`
- `--pxpl` — Pixel Music `.pxpl` backup archive

### Show last sync time

    python -m lsm stats

## How it works

1. Reads `.env` for credentials
2. `sync` calls the Last.fm API, gets scrobbles newer than the last state file timestamp, POSTs them in batches of 1000 to ListenBrainz
3. `merge` parses each backup format, normalizes tracks, POSTs them in batches
4. Writes the latest timestamp to `.lsm_state.json` so future runs only push new data

## Platform status

| Platform | Status |
|----------|--------|
| Linux | Tested |
| macOS | Untested |
| Windows | Untested |

## License

MIT — see [LICENSE](LICENSE).
