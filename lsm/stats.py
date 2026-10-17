import os, json, time
from datetime import datetime

STATE = ".lsm_state.json"

def run():
    if not os.path.exists(STATE):
        print("No sync state yet. Run: python -m lsm sync")
        return
    try:
        s = json.load(open(STATE))
        ts = s.get("last_sync_uts")
        if not ts:
            print("Last sync: never")
            return
        dt = datetime.fromtimestamp(ts)
        delta = int(time.time() - ts)
        if delta < 60:      ago = f"{delta}s ago"
        elif delta < 3600:  ago = f"{delta//60}m ago"
        elif delta < 86400: ago = f"{delta//3600}h ago"
        else:               ago = f"{delta//86400}d ago"
        print(f"Last sync: {dt.strftime('%Y-%m-%d %H:%M:%S')}  ({ago})")
    except Exception as e:
        print(f"state read error: {e}")
