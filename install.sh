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

missing_required=()
missing_optional=()

command -v umu-run >/dev/null 2>&1 || missing_required+=("umu-launcher")
command -v python3 >/dev/null 2>&1 || missing_required+=("python")
python3 -c "import vdf" >/dev/null 2>&1 || missing_optional+=("python-vdf")

install_pacman_pkgs() {
	local pkgs=("$@")
	if ! command -v pacman >/dev/null 2>&1; then
		echo "    pacman not found -- install manually: ${pkgs[*]}"
		return
	fi
	read -r -p "    Install ${pkgs[*]} via pacman now? [y/N] " reply
	if [[ "$reply" =~ ^[Yy]$ ]]; then
		sudo pacman -S --needed "${pkgs[@]}"
	else
		echo "    Skipped. Install later with: sudo pacman -S ${pkgs[*]}"
	fi
}

if [ ${#missing_required[@]} -gt 0 ]; then
	echo "==> Missing required dependencies: ${missing_required[*]}"
	install_pacman_pkgs "${missing_required[@]}"
fi

if [ ${#missing_optional[@]} -gt 0 ]; then
	echo "==> Missing optional dependency: ${missing_optional[*]}"
	echo "    (only used for the local co-op / split-screen filter in the TUI;"
	echo "    everything else works fine without it)"
	install_pacman_pkgs "${missing_optional[@]}"
fi

# --- Deploy files --------------------------------------------------------

mkdir -p "$BIN_DEST" "$SHARE_DEST" "$STATE_DEST"

install -m 755 "$SCRIPT_DIR/bin/rpt-anywhere" "$BIN_DEST/rpt-anywhere"
install -m 755 "$SCRIPT_DIR/bin/rpt-select" "$BIN_DEST/rpt-select"
install -m 644 "$SCRIPT_DIR/share/resolve.py" "$SHARE_DEST/resolve.py"
install -m 644 "$SCRIPT_DIR/share/registry.py" "$SHARE_DEST/registry.py"
install -m 644 "$SCRIPT_DIR/share/tui.py" "$SHARE_DEST/tui.py"
install -m 644 "$SCRIPT_DIR/share/appinfo.py" "$SHARE_DEST/appinfo.py"

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
