#!/usr/bin/env python3
"""Resolve the active game from the registry and print it as shell-safe
`export` statements for rpt-anywhere to `eval`. Keeping this logic in a real
argv-driven script (instead of interpolating shell variables into an inline
python -c string) avoids both quoting bugs on paths with spaces and shell
injection via game names or paths.
"""
import json
import shlex
import sys

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

for key in ("appid", "exe", "proton"):
    print(f"export RPT_{key.upper()}={shlex.quote(str(game[key]))}")
print(f"export RPT_ARGS={shlex.quote(str(game.get('args') or ''))}")
print(f"export RPT_NAME={shlex.quote(active_name)}")
