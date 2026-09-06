"""Resolve and launch Proton games using only what Steam itself already
installs -- no umu-launcher, no third-party runtime. Steam always installs a
Steam Linux Runtime container alongside the first Proton game you ever run,
and every Proton build ships a toolmanifest.vdf declaring which runtime
container it needs (this varies by Proton build: GE-Proton10-34 requires the
older 'sniper' container while Proton - Experimental requires the newer
'SteamLinuxRuntime_4', for example -- so this is read per-build, never
hardcoded).

This reproduces the exact invocation Steam itself uses internally:
    <runtime>/_v2-entry-point --verb=run -- <proton>/proton run <exe> [args]

(verb=run, not waitforexitandrun -- the latter deadlocks waiting on
wineserver when invoked outside Steam's own session tracking.)
"""
import os
import re

import steamutil

COMPAT_TOOLS_DIR = os.path.join(steamutil.STEAM_ROOT, "compatibilitytools.d")
COMMON_DIR = os.path.join(steamutil.STEAM_ROOT, "steamapps", "common")


class RequiredRuntimeMissing(Exception):
    """Raised when a Proton build declares a required Steam Linux Runtime
    container that isn't actually installed -- distinct from a build that
    doesn't require one at all, since silently falling back to a bare
    Proton invocation in that case tends to fail in confusing ways."""

    def __init__(self, runtime_appid):
        self.runtime_appid = runtime_appid
        super().__init__(f"required Steam Linux Runtime container (appid {runtime_appid}) not installed")


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
    build requires, or None if it doesn't declare one at all (very old
    Proton). Raises RequiredRuntimeMissing if one IS declared but isn't
    installed -- that's a distinct, much more common failure than "doesn't
    need one", and silently treating it the same way leads to a confusing
    launch failure instead of a clear error."""
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
    runtime_appid = m.group(1)
    info = steamutil.read_appmanifest(runtime_appid)
    if info is None or not os.path.isdir(info["path"]):
        raise RequiredRuntimeMissing(runtime_appid)
    return info["path"]
