"""Shared helpers for reading Steam's local, plain-text appmanifest files.
No network access, no Steam client interaction -- just parsing files Steam
already wrote to disk.
"""
import glob
import os
import re

STEAM_ROOT = os.path.expanduser("~/.local/share/Steam")


def read_appmanifest(appid):
    """Returns {"appid": str, "name": str, "path": install_dir} for one
    installed app, or None if its appmanifest can't be found/parsed."""
    path = os.path.join(STEAM_ROOT, "steamapps", f"appmanifest_{appid}.acf")
    if not os.path.exists(path):
        return None
    try:
        with open(path, errors="ignore") as f:
            text = f.read()
    except OSError:
        return None
    m_name = re.search(r'"name"\s*"([^"]*)"', text)
    m_dir = re.search(r'"installdir"\s*"([^"]*)"', text)
    if not (m_name and m_dir):
        return None
    install_path = os.path.join(STEAM_ROOT, "steamapps", "common", m_dir.group(1))
    return {"appid": str(appid), "name": m_name.group(1), "path": install_path}


def scan_installed_apps():
    """Returns [(appid, name, install_path), ...] for every installed app
    with a resolvable appmanifest and an install directory that exists."""
    apps = []
    for path in glob.glob(os.path.join(STEAM_ROOT, "steamapps", "appmanifest_*.acf")):
        m = re.search(r"appmanifest_(\d+)\.acf$", path)
        if not m:
            continue
        info = read_appmanifest(m.group(1))
        if info and os.path.isdir(info["path"]):
            apps.append((info["appid"], info["name"], info["path"]))
    apps.sort(key=lambda a: a[1].lower())
    return apps
