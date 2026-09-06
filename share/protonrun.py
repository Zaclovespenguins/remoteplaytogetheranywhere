"""Resolve and launch Proton games using only what Steam itself already
installs -- no umu-launcher, no third-party runtime. Steam always installs a
Steam Linux Runtime container alongside the first Proton game you ever run,
and every Proton build ships a toolmanifest.vdf declaring which runtime
container it needs (this varies by Proton build: GE-Proton10-34 requires the
older 'sniper' container while Proton - Experimental requires the newer
'SteamLinuxRuntime_4', for example -- so this is read per-build, never
hardcoded).

This reproduces the exact invocation Steam itself uses internally:
    <runtime>/_v2-entry-point --verb=waitforexitandrun -- <proton>/proton \\
        waitforexitandrun <exe> [args]
"""
import os
import re

import steamutil

COMPAT_TOOLS_DIR = os.path.join(steamutil.STEAM_ROOT, "compatibilitytools.d")
COMMON_DIR = os.path.join(steamutil.STEAM_ROOT, "steamapps", "common")


def list_proton_installations():
    """Returns [(display_name, proton_dir), ...]: custom Proton builds under
    compatibilitytools.d, plus official Valve builds under steamapps/common
    (identified by folder name starting with 'Proton')."""
    results = []
    if os.path.isdir(COMPAT_TOOLS_DIR):
        for entry in sorted(os.listdir(COMPAT_TOOLS_DIR)):
            full = os.path.join(COMPAT_TOOLS_DIR, entry)
            if os.path.isfile(os.path.join(full, "proton")):
                results.append((entry, full))
    if os.path.isdir(COMMON_DIR):
        for entry in sorted(os.listdir(COMMON_DIR)):
            if entry.startswith("Proton") and os.path.isfile(os.path.join(COMMON_DIR, entry, "proton")):
                results.append((entry, os.path.join(COMMON_DIR, entry)))
    return results


def find_proton_dir(name):
    """name is a display name, e.g. 'GE-Proton10-34' or 'Proton - Experimental'."""
    for base in (COMPAT_TOOLS_DIR, COMMON_DIR):
        candidate = os.path.join(base, name)
        if os.path.isfile(os.path.join(candidate, "proton")):
            return candidate
    return None


def find_required_runtime_dir(proton_dir):
    """Returns the Steam Linux Runtime container's install path this Proton
    build requires, or None if it doesn't declare one (very old Proton)."""
    manifest_path = os.path.join(proton_dir, "toolmanifest.vdf")
    if not os.path.exists(manifest_path):
        return None
    try:
        with open(manifest_path, errors="ignore") as f:
            text = f.read()
    except OSError:
        return None
    m = re.search(r'"require_tool_appid"\s*"(\d+)"', text)
    if not m:
        return None
    info = steamutil.read_appmanifest(m.group(1))
    if info is None or not os.path.isdir(info["path"]):
        return None
    return info["path"]
