#!/usr/bin/env python3
"""Registry helper for rpt-select. All game names/paths arrive as argv, never
interpolated into inline python source, so odd characters in a game name or
install path can't break or inject into the script.
"""
import json
import os
import sys

REGISTRY = os.path.expanduser("~/.local/share/rpt-anywhere/games.json")


def load():
    if not os.path.exists(REGISTRY):
        return {}
    with open(REGISTRY) as f:
        return json.load(f)


def save(data):
    tmp = REGISTRY + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, REGISTRY)


def cmd_list(_args):
    for name in sorted(load()):
        print(name)


def cmd_has(args):
    print("yes" if args[0] in load() else "no")


def cmd_add(args):
    if len(args) < 3:
        print("usage: registry.py add <name> <appid> <exe> [proton] [args]", file=sys.stderr)
        sys.exit(1)
    name, appid, exe = args[0], args[1], args[2]
    proton = args[3] if len(args) > 3 else "GE-Proton10-34"
    extra_args = args[4] if len(args) > 4 else ""
    if not os.path.isfile(exe):
        print(f"warning: exe does not exist (yet): {exe}", file=sys.stderr)
    data = load()
    data[name] = {"appid": appid, "exe": exe, "proton": proton, "args": extra_args}
    save(data)
    print(f"Added/updated '{name}'.")


def cmd_remove(args):
    if len(args) < 1:
        print("usage: registry.py remove <name>", file=sys.stderr)
        sys.exit(1)
    data = load()
    if args[0] not in data:
        print(f"'{args[0]}' not in registry.", file=sys.stderr)
        sys.exit(1)
    del data[args[0]]
    save(data)
    print(f"Removed '{args[0]}'.")


COMMANDS = {"list": cmd_list, "has": cmd_has, "add": cmd_add, "remove": cmd_remove}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"usage: registry.py <{'|'.join(COMMANDS)}> [args...]", file=sys.stderr)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
