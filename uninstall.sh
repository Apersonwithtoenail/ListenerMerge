#!/usr/bin/env bash
set -e
rm -f "$HOME/.local/bin/lsm"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/listenermerge.svg"
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
echo "✅ Listenermerge removed"
