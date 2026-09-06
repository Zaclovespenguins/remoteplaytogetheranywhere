#!/usr/bin/env python3
"""Resolve the active game from the registry, plus its Proton binary and
required runtime container, and print it all as shell-safe `export`
statements for rpt-anywhere to `eval`. Keeping this logic in a real
argv-driven script (instead of interpolating shell variables into an inline
python -c string) avoids both quoting bugs on paths with spaces and shell
injection via game names or paths.
"""
import json
import os
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import protonrun  # noqa: E402


def fail(msg):
    print(f"echo {shlex.quote('rpt-anywhere: ' + msg)} >&2; exit 1")
    sys.exit(0)


if len(sys.argv) != 3:
    fail("resolve.py requires <registry_path> <active_name>")

registry_path, active_name = sys.argv[1], sys.argv[2]

try:
    with open(registry_path) as f:
        registry = json.load(f)
except (OSError, json.JSONDecodeError) as e:
    fail(f"could not read registry {registry_path}: {e}")

game = registry.get(active_name)
if game is None:
    fail(f"'{active_name}' not found in registry {registry_path}")

missing = [k for k in ("appid", "exe", "proton") if not game.get(k)]
if missing:
    fail(f"registry entry '{active_name}' missing required field(s): {', '.join(missing)}")

proton_dir = protonrun.find_proton_dir(game["proton"])
if proton_dir is None:
    fail(f"Proton build '{game['proton']}' not found (not under compatibilitytools.d or steamapps/common)")

runtime_dir = protonrun.find_required_runtime_dir(proton_dir)

for key in ("appid", "exe", "proton"):
    print(f"export RPT_{key.upper()}={shlex.quote(str(game[key]))}")
print(f"export RPT_ARGS={shlex.quote(str(game.get('args') or ''))}")
print(f"export RPT_NAME={shlex.quote(active_name)}")
print(f"export RPT_PROTON_BIN={shlex.quote(os.path.join(proton_dir, 'proton'))}")
print(f"export RPT_RUNTIME_ENTRY={shlex.quote(os.path.join(runtime_dir, '_v2-entry-point') if runtime_dir else '')}")
