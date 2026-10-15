import argparse
from . import config

def main():
    p = argparse.ArgumentParser(
        prog="lsm",
        description="Listening Stats Merger - sync Last.fm & local backups to ListenBrainz"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sync", help="Sync new Last.fm scrobbles → ListenBrainz")

    pm = sub.add_parser("merge", help="Merge local Spotify / YTMusic / PixelMusic backups")
    pm.add_argument("--spotify", default="Spotify Extended Streaming History")
    pm.add_argument("--takeout", default="Takeout")
    pm.add_argument("--pxpl", default=None)

    sub.add_parser("stats", help="Show last sync timestamp")

    args = p.parse_args()
    if not config.check():
        return

    if args.cmd == "sync":
        from . import sync_lastfm
        sync_lastfm.run()
    elif args.cmd == "merge":
        from . import merge
        merge.run(args.spotify, args.takeout, args.pxpl)
    elif args.cmd == "stats":
        from . import stats
        stats.run()

if __name__ == "__main__":
    main()
