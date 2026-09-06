#!/usr/bin/env bash
# Installer for rpt-anywhere: enables Steam Remote Play Together on games
# whose publisher disabled it, via a donor-game launch-options trick.
# Safe to re-run to upgrade -- never touches your existing games.json/active
# selection.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BIN_DEST="$HOME/.local/bin"
SHARE_DEST="$HOME/.local/share/rpt-anywhere"
STATE_DEST="$HOME/.local/state/rpt-anywhere"

echo "==> Installing rpt-anywhere from $SCRIPT_DIR"

# --- Dependency checks -------------------------------------------------
#
# No third-party launcher required: Proton games are run directly through
# whatever Proton build and Steam Linux Runtime container Steam itself
# already installed. This also means no extra dependency is needed on
# SteamOS's read-only root -- everything used here (python3, Steam's own
# Proton/runtime) is already present on any Steam install.

if ! command -v python3 >/dev/null 2>&1; then
	echo "==> FATAL: python3 not found. It should already be installed alongside Steam."
	exit 1
fi

if ! python3 -c "import vdf" >/dev/null 2>&1; then
	echo "==> Optional: the 'vdf' python package isn't installed."
	echo "    (only used for the local co-op / split-screen filter in the TUI's"
	echo "    game-scan flow; everything else works fine without it)"
	if command -v pip3 >/dev/null 2>&1; then
		read -r -p "    Install it now with 'pip3 install --user vdf'? [y/N] " reply
		if [[ "$reply" =~ ^[Yy]$ ]]; then
			pip3 install --user vdf
		else
			echo "    Skipped. Install later with: pip3 install --user vdf"
		fi
	else
		echo "    pip3 not found -- install later with: pip3 install --user vdf"
	fi
fi

# --- Deploy files --------------------------------------------------------

mkdir -p "$BIN_DEST" "$SHARE_DEST" "$STATE_DEST"

install -m 755 "$SCRIPT_DIR/bin/rpt-anywhere" "$BIN_DEST/rpt-anywhere"
install -m 755 "$SCRIPT_DIR/bin/rpt-select" "$BIN_DEST/rpt-select"
install -m 644 "$SCRIPT_DIR/share/resolve.py" "$SHARE_DEST/resolve.py"
install -m 644 "$SCRIPT_DIR/share/registry.py" "$SHARE_DEST/registry.py"
install -m 644 "$SCRIPT_DIR/share/tui.py" "$SHARE_DEST/tui.py"
install -m 644 "$SCRIPT_DIR/share/appinfo.py" "$SHARE_DEST/appinfo.py"
install -m 644 "$SCRIPT_DIR/share/steamutil.py" "$SHARE_DEST/steamutil.py"
install -m 644 "$SCRIPT_DIR/share/protonrun.py" "$SHARE_DEST/protonrun.py"

# Never overwrite an existing registry/selection on upgrade.
if [ ! -f "$SHARE_DEST/games.json" ]; then
	echo "{}" > "$SHARE_DEST/games.json"
fi

echo "==> Installed rpt-anywhere and rpt-select to $BIN_DEST"

case ":$PATH:" in
	*":$BIN_DEST:"*) ;;
	*) echo "==> NOTE: $BIN_DEST is not on your PATH. Add this to your shell rc:" ;
	   echo "        export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac

cat <<EOF

==> Next steps:
    1. Run 'rpt-select' to add games to the registry (it can scan your
       installed Steam library for you).
    2. In Steam, pick an already-owned game that already has Remote Play
       Together enabled to act as the reusable "donor". Set its Launch
       Options to:
           $BIN_DEST/rpt-anywhere %command%
    3. Run 'rpt-select <name>' (or use the TUI) to choose which game
       launches when you hit Play on the donor.
EOF
