import os, json

STATE = ".lsm_state.json"

def run():
    if os.path.exists(STATE):
        s = json.load(open(STATE))
        print(f"Last sync: {s.get('last_sync_uts', 'never')}")
    else:
        print("No sync state yet. Run: python -m lsm sync")
