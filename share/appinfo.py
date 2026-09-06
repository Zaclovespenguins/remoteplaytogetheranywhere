"""Read Steam's locally-cached appinfo.vdf to check which installed games
have local co-op / split-screen support -- entirely offline, since Steam
already downloaded and cached this data itself. No network access here.

Binary format reverse-engineered by SteamDatabase/SteamAppInfo; parsed here
using the `vdf` package's binary_loads(key_table=...), which already supports
the v41+ out-of-band string table for keys.
"""
import os
import struct

try:
    import vdf
except ImportError:
    vdf = None

APPINFO_PATH = os.path.expanduser("~/.local/share/Steam/appcache/appinfo.vdf")

# Steam feature-category IDs (from SteamDB). 24 = Shared/Split Screen,
# 39 = Shared/Split Screen Co-op -- i.e. "local co-op / split screen".
LOCAL_MULTIPLAYER_CATEGORY_IDS = {24, 39}

# 44 = Remote Play Together -- games that already have this natively don't
# need the donor-game trick, so candidate lists should exclude them.
REMOTE_PLAY_TOGETHER_CATEGORY_ID = 44


def _read_cstring(fp):
    buf = b""
    while True:
        b = fp.read(1)
        if b in (b"\x00", b""):
            return buf.decode("utf-8", "replace")
        buf += b


def load_categories():
    """Returns {appid: set(category_id, ...)}. Returns {} if appinfo.vdf is
    missing or fails to parse for any reason -- callers should treat that as
    'no category info available' and fall back to showing everything."""
    if vdf is None or not os.path.exists(APPINFO_PATH):
        return {}

    result = {}
    try:
        with open(APPINFO_PATH, "rb") as fp:
            magic_full = struct.unpack("<I", fp.read(4))[0]
            version = magic_full & 0xFF
            if (magic_full >> 8) != 0x075644:
                return {}
            fp.read(4)  # universe, unused

            key_table = None
            if version >= 41:
                string_table_offset = struct.unpack("<q", fp.read(8))[0]
                here = fp.tell()
                fp.seek(string_table_offset)
                count = struct.unpack("<I", fp.read(4))[0]
                key_table = [_read_cstring(fp) for _ in range(count)]
                fp.seek(here)

            while True:
                appid_bytes = fp.read(4)
                if len(appid_bytes) < 4:
                    break
                appid = struct.unpack("<I", appid_bytes)[0]
                if appid == 0:
                    break
                size = struct.unpack("<I", fp.read(4))[0]
                record_start = fp.tell()
                fp.read(8 + 8 + 20 + 4)  # info_state, last_updated, pics_token, text_sha1, change_number
                if version >= 40:
                    fp.read(20)  # binary_data_hash
                kv_len = size - (fp.tell() - record_start)
                kv_bytes = fp.read(kv_len)

                try:
                    data = vdf.binary_loads(kv_bytes, key_table=key_table, raise_on_remaining=False)
                except Exception:
                    continue

                try:
                    (inner,) = data.values()
                    cat = inner.get("common", {}).get("category", {})
                except Exception:
                    continue

                ids = set()
                for k in cat:
                    if k.startswith("category_"):
                        try:
                            ids.add(int(k.split("_", 1)[1]))
                        except ValueError:
                            pass
                result[appid] = ids
    except (OSError, struct.error):
        return {}

    return result


def has_local_multiplayer(categories_by_appid, appid):
    cats = categories_by_appid.get(int(appid))
    if cats is None:
        return None  # unknown -- appid not found in appinfo.vdf at all
    return bool(cats & LOCAL_MULTIPLAYER_CATEGORY_IDS)


def has_official_remote_play_together(categories_by_appid, appid):
    cats = categories_by_appid.get(int(appid))
    if cats is None:
        return None  # unknown -- appid not found in appinfo.vdf at all
    return REMOTE_PLAY_TOGETHER_CATEGORY_ID in cats
