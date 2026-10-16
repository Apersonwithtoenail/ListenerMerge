#!/usr/bin/env bash
# install.sh — install Listenermerge to ~/.local/bin
set -e

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
APPS="$HOME/.local/share/applications"
mkdir -p "$BIN" "$ICONS" "$APPS"

# wrapper — runs from the repo dir so lsm module resolves
cat > "$BIN/lsm" <<WRAP
#!/usr/bin/env bash
cd "$REPO" && exec /usr/bin/python3 -m lsm "\$@"
WRAP
chmod +x "$BIN/lsm"

# icon
cp "$REPO/assets/icon.svg" "$ICONS/listenermerge.svg" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "✅ Listenermerge installed"
echo "   Run: lsm sync   |   lsm merge --help   |   lsm stats"
echo "   Uninstall: ./uninstall.sh"
