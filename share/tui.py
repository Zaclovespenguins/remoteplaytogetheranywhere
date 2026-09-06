#!/usr/bin/env python3
"""Interactive terminal UI for rpt-select, shown when it's run with no
arguments. Lets you browse configured games, pick the active one, add a new
game (optionally by scanning your installed Steam library instead of typing
paths by hand), and remove entries -- all without hand-editing games.json.
"""
import curses
import curses.textpad
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry  # noqa: E402
import appinfo  # noqa: E402
import steamutil  # noqa: E402
import protonrun  # noqa: E402

SHOW_ALL_SENTINEL = object()

STATE_DIR = os.path.expanduser("~/.local/state/rpt-anywhere")
ACTIVE_FILE = os.path.join(STATE_DIR, "active")

EXE_IGNORE_PATTERNS = re.compile(
    r"(uninstall|unins0\d*|vc_?redist|dxsetup|dxwebsetup|directx|"
    r"crashhandler|crashpad|battleye|easyanticheat|eac_?launcher|"
    r"dotnet|vcredist|redist|installer|helper\.exe$|updater\.exe$)",
    re.IGNORECASE,
)


def load_active():
    if os.path.exists(ACTIVE_FILE):
        with open(ACTIVE_FILE) as f:
            return f.read().strip()
    return None


def set_active(name):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(ACTIVE_FILE, "w") as f:
        f.write(name)


def scan_steam_apps():
    """Return [(appid, name, installdir_path), ...] for every installed app."""
    return steamutil.scan_installed_apps()


def find_candidate_exes(install_path):
    candidates = []
    for root, _dirs, files in os.walk(install_path):
        for fn in files:
            if fn.lower().endswith(".exe") and not EXE_IGNORE_PATTERNS.search(fn):
                candidates.append(os.path.join(root, fn))
    # Prefer shallower paths and shorter names first (usually the real launcher).
    candidates.sort(key=lambda p: (p.count(os.sep), len(p)))
    return candidates


def list_proton_versions():
    """Only real, installed Proton builds -- each one is resolved again at
    launch time (proton binary + required runtime container), so listing a
    build that doesn't actually exist would just fail later at launch."""
    return [name for name, _path in protonrun.list_proton_installations()]


class TUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)  # selected row
        curses.init_pair(2, curses.COLOR_GREEN, -1)  # active marker
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # status/errors
        self.status = "↑/↓ select   Enter=make active   a=add   d=delete   q=quit"

    def draw(self, games, names, sel):
        stdscr = self.stdscr
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        active = load_active()

        title = " RPT Anywhere "
        stdscr.addstr(0, max(0, (w - len(title)) // 2), title, curses.A_BOLD)
        stdscr.addstr(1, 2, "Remote Play Together for any Steam title (via a donor game's launch options)")

        header = f"  {'':2}{'NAME':<28}{'APPID':<12}{'PROTON':<20}"
        stdscr.addstr(3, 2, header[: w - 4], curses.A_UNDERLINE)

        if not names:
            stdscr.addstr(5, 4, "No games configured yet. Press 'a' to add one.", curses.color_pair(3))
        else:
            for i, name in enumerate(names):
                g = games[name]
                marker = "*" if name == active else " "
                row = f"{marker} {name:<28}{g.get('appid',''):<12}{g.get('proton',''):<20}"
                row = row[: w - 6]
                y = 5 + i
                if y >= h - 3:
                    break
                attr = curses.color_pair(1) if i == sel else curses.A_NORMAL
                if marker == "*" and i != sel:
                    attr = curses.color_pair(2)
                stdscr.addstr(y, 2, row, attr)

        active_line = f"Active: {active or '(none selected)'}"
        stdscr.addstr(h - 3, 2, active_line[: w - 4], curses.A_BOLD)
        stdscr.addstr(h - 2, 2, self.status[: w - 4], curses.color_pair(3))
        stdscr.refresh()

    def input_line(self, prompt, default=""):
        stdscr = self.stdscr
        h, w = stdscr.getmaxyx()
        y = h - 1
        stdscr.addstr(y, 0, " " * (w - 1))
        label = f"{prompt}: "
        stdscr.addstr(y, 0, label)
        curses.curs_set(1)
        win = curses.newwin(1, max(10, w - len(label) - 1), y, len(label))
        win.addstr(0, 0, default)
        box = curses.textpad.Textbox(win, insert_mode=True)
        stdscr.refresh()
        text = box.edit().strip()
        curses.curs_set(0)
        return text

    def choose_from_list(self, title, items, formatter=str, searchable=True):
        """items: list of arbitrary objects. Returns the chosen item or None on
        cancel. When searchable, typing narrows the list live by substring
        match against the formatted text (SHOW_ALL_SENTINEL, if present, is
        always kept visible regardless of the query)."""
        if not items:
            return None
        sel = 0
        query = ""
        stdscr = self.stdscr
        while True:
            if query:
                filtered = [
                    i for i in items
                    if i is SHOW_ALL_SENTINEL or query.lower() in formatter(i).lower()
                ]
            else:
                filtered = items
            sel = max(0, min(sel, len(filtered) - 1))

            stdscr.erase()
            h, w = stdscr.getmaxyx()
            stdscr.addstr(0, 2, title, curses.A_BOLD)
            if searchable:
                stdscr.addstr(1, 2, "↑/↓ move   Enter=choose   Esc=cancel   type to search", curses.color_pair(3))
                stdscr.addstr(2, 2, f"Search: {query}"[: w - 4])
                list_start = 4
            else:
                stdscr.addstr(1, 2, "↑/↓ move   Enter=choose   Esc=cancel", curses.color_pair(3))
                list_start = 3
            if not filtered:
                stdscr.addstr(list_start, 4, "(no matches)", curses.color_pair(3))
            for i, item in enumerate(filtered):
                y = list_start + i
                if y >= h - 1:
                    break
                attr = curses.color_pair(1) if i == sel else curses.A_NORMAL
                stdscr.addstr(y, 2, formatter(item)[: w - 4], attr)
            stdscr.refresh()
            key = stdscr.getch()
            if key == curses.KEY_UP:
                sel = (sel - 1) % len(filtered) if filtered else 0
            elif key == curses.KEY_DOWN:
                sel = (sel + 1) % len(filtered) if filtered else 0
            elif key in (curses.KEY_ENTER, 10, 13):
                if filtered:
                    return filtered[sel]
            elif key == 27:  # Esc
                return None
            elif searchable and key in (curses.KEY_BACKSPACE, 127, 8):
                query = query[:-1]
                sel = 0
            elif searchable and 32 <= key <= 126:
                query += chr(key)
                sel = 0
            elif not searchable and key in (ord("k"),):
                sel = (sel - 1) % len(filtered) if filtered else 0
            elif not searchable and key in (ord("j"),):
                sel = (sel + 1) % len(filtered) if filtered else 0

    def confirm(self, message):
        stdscr = self.stdscr
        h, w = stdscr.getmaxyx()
        y = h - 1
        stdscr.addstr(y, 0, " " * (w - 1))
        stdscr.addstr(y, 0, f"{message} [y/N]: ")
        stdscr.refresh()
        key = stdscr.getch()
        return key in (ord("y"), ord("Y"))

    def flow_add_manual(self):
        name = self.input_line("Display name")
        if not name:
            self.status = "Add cancelled (no name given)."
            return
        appid = self.input_line("Steam AppID")
        exe = self.input_line("Full path to game executable")
        proton_choice = self.choose_from_list(
            "Pick a Proton version (Esc to type one manually)", list_proton_versions()
        )
        proton = proton_choice or self.input_line("Proton version/codename", "GE-Proton")
        args = self.input_line("Extra launch args (optional)")
        data = registry.load()
        data[name] = {"appid": appid, "exe": exe, "proton": proton, "args": args}
        registry.save(data)
        self.status = f"Added '{name}'."

    def pick_installed_app(self, apps, show_all=False):
        """Filters to games with local co-op / split-screen support that
        DON'T already have official Remote Play Together (no point routing
        those through a donor -- Steam already offers RPT for them directly),
        unless show_all is set or category info isn't available locally. A
        'show all' escape hatch is offered at the bottom of the list either
        way."""
        categories = appinfo.load_categories()
        if categories and not show_all:
            filtered = [
                a
                for a in apps
                if appinfo.has_local_multiplayer(categories, a[0]) is True
                and appinfo.has_official_remote_play_together(categories, a[0]) is not True
            ]
            title = "Pick an installed Steam game (local co-op/split-screen, no official RPT)"
        else:
            filtered = apps
            title = "Pick an installed Steam game (all installed games)"
            if not categories and not show_all:
                title += " -- no local category data available"

        items = list(filtered)
        if not show_all and categories:
            items.append(SHOW_ALL_SENTINEL)

        def fmt(item):
            if item is SHOW_ALL_SENTINEL:
                return "-- Show all installed games --"
            appid, name, _path = item
            return f"{name}  (appid {appid})"

        picked = self.choose_from_list(title, items, formatter=fmt)
        if picked is SHOW_ALL_SENTINEL:
            return self.pick_installed_app(apps, show_all=True)
        return picked

    def flow_add_scanned(self):
        apps = scan_steam_apps()
        if not apps:
            self.status = "No installed Steam apps found to scan."
            return
        picked = self.pick_installed_app(apps)
        if picked is None:
            self.status = "Add cancelled."
            return
        appid, steam_name, install_path = picked
        exes = find_candidate_exes(install_path)
        if exes:
            exe = self.choose_from_list(
                f"Pick the executable for {steam_name} (Esc to type a path manually)",
                exes,
                formatter=lambda p: os.path.relpath(p, install_path),
            )
            if exe is None:
                exe = self.input_line("Full path to game executable")
        else:
            exe = self.input_line("No .exe found automatically -- full path to executable", install_path + "/")
        proton_choice = self.choose_from_list(
            "Pick a Proton version (Esc to type one manually)", list_proton_versions()
        )
        proton = proton_choice or self.input_line("Proton version/codename", "GE-Proton")
        args = self.input_line("Extra launch args (optional)")
        name = self.input_line("Display name", steam_name)
        if not name:
            self.status = "Add cancelled (no name given)."
            return
        data = registry.load()
        data[name] = {"appid": appid, "exe": exe, "proton": proton, "args": args}
        registry.save(data)
        self.status = f"Added '{name}' from your Steam library."

    def run(self):
        sel = 0
        while True:
            data = registry.load()
            names = sorted(data)
            if sel >= len(names):
                sel = max(0, len(names) - 1)
            self.draw(data, names, sel)
            key = self.stdscr.getch()

            if key in (ord("q"), ord("Q")):
                return
            elif key in (curses.KEY_UP, ord("k")) and names:
                sel = (sel - 1) % len(names)
            elif key in (curses.KEY_DOWN, ord("j")) and names:
                sel = (sel + 1) % len(names)
            elif key in (curses.KEY_ENTER, 10, 13) and names:
                set_active(names[sel])
                self.status = f"Active game set to: {names[sel]}"
            elif key in (ord("d"), ord("D")) and names:
                if self.confirm(f"Remove '{names[sel]}' from the registry?"):
                    data = registry.load()
                    del data[names[sel]]
                    registry.save(data)
                    self.status = f"Removed '{names[sel]}'."
            elif key in (ord("a"), ord("A")):
                choice = self.choose_from_list(
                    "Add a game", ["Scan installed Steam library", "Enter details manually"]
                )
                if choice == "Scan installed Steam library":
                    self.flow_add_scanned()
                elif choice == "Enter details manually":
                    self.flow_add_manual()


def main(stdscr):
    TUI(stdscr).run()


if __name__ == "__main__":
    curses.wrapper(main)
