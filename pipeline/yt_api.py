"""Fetch video metadata through the official YouTube Data API v3.

Reads the key from the YOUTUBE_API_KEY environment variable and never prints it.
Writes the same files the yt-dlp fetchers wrote, so build_data.py is unchanged.

  python3 pipeline/yt_api.py channels [--force]   all channels in channels.json (~3,000 units)
  python3 pipeline/yt_api.py reddit               videos linked on Reddit (~30 units)
  python3 pipeline/yt_api.py interviews           one search per new figure (100 units each); with --force, refresh known interviews' metadata cheaply
  python3 pipeline/yt_api.py all
  python3 pipeline/yt_api.py refresh              refresh stats of videos already in the library (~1,200 units)
"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
API = "https://www.googleapis.com/youtube/v3"
KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()
PL_KEEP = re.compile(r"canslim|can slim|breadth|cycle|momentum|technical|chart|swing|breakout|stage|minervini|o.?neil|ibd|trend|hurst|relative strength|elliott|wave|wyckoff|vsa|volume|candle|pattern|interview|cfa|level|ethic|quant|econom|financial (statement|reporting)|fsa|corporate|equity|fixed income|bond|derivativ|option|futures|swap|alternative|portfolio|wealth|valuation|risk|private|mock|exam|formula|essay|frm", re.I)
units = 0


class QuotaExceeded(Exception):
    pass


def call(endpoint, cost=1, **params):
    global units
    url = f"{API}/{endpoint}?{urllib.parse.urlencode({**params, 'key': KEY})}"
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                units += cost
                return json.load(r)
        except urllib.error.HTTPError as e:
            units += cost
            try:
                reason = json.loads(e.read())["error"]["errors"][0]["reason"]
            except Exception:
                reason = str(e.code)
            if reason in ("quotaExceeded", "dailyLimitExceeded"):
                raise QuotaExceeded()
            if reason in ("keyInvalid", "accessNotConfigured", "forbidden", "ipRefererBlocked"):
                sys.exit(f"YouTube API refused the key ({reason}). Check that the key is right and YouTube Data API v3 is enabled.")
            if e.code in (400, 404):
                return None
            time.sleep(5 * (i + 1))
        except Exception:
            time.sleep(5 * (i + 1))
    return None


def iso_seconds(d):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return None
    dd, h, mi, s = (int(x or 0) for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + s


def ts(iso):
    try:
        return int(time.mktime(time.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S")))
    except Exception:
        return None


def video_meta(ids):
    out = {}
    ids = list(dict.fromkeys(ids))
    for i in range(0, len(ids), 50):
        d = call("videos", part="snippet,contentDetails,statistics", id=",".join(ids[i:i + 50]), maxResults=50)
        for it in (d or {}).get("items", []):
            sn, st = it["snippet"], it.get("statistics", {})
            out[it["id"]] = {"id": it["id"], "title": sn["title"], "channel": sn.get("channelTitle"), "channel_id": sn.get("channelId"),
                             "duration": iso_seconds(it["contentDetails"].get("duration")),
                             "view_count": int(st["viewCount"]) if "viewCount" in st else None,
                             "timestamp": ts(sn.get("publishedAt")), "live_status": sn.get("liveBroadcastContent")}
    return out


def playlist_ids(pid, limit=20000):
    ids, token = [], None
    while len(ids) < limit:
        d = call("playlistItems", part="contentDetails", playlistId=pid, maxResults=50, **({"pageToken": token} if token else {}))
        if not d:
            break
        ids += [it["contentDetails"]["videoId"] for it in d.get("items", [])]
        token = d.get("nextPageToken")
        if not token:
            break
    return ids


def slim(m):
    return {k: m[k] for k in ("id", "title", "duration", "view_count", "timestamp", "live_status") if m.get(k) is not None}


def fetch_channel(ch, force):
    dest = RAW / "channels" / f"{ch['id']}.json"
    if dest.exists() and not force and json.loads(dest.read_text()).get("source") == "api":
        return
    d = call("channels", part="snippet,contentDetails,statistics", id=ch["id"])
    if not d or not d.get("items"):
        print(f"  not found: {ch['name']}", flush=True)
        return
    it = d["items"][0]
    ids = playlist_ids(it["contentDetails"]["relatedPlaylists"]["uploads"])
    meta = video_meta(ids)
    pls, token = [], None
    while True:
        p = call("playlists", part="snippet,contentDetails", channelId=ch["id"], maxResults=50, **({"pageToken": token} if token else {}))
        if not p:
            break
        pls += p.get("items", [])
        token = p.get("nextPageToken")
        if not token:
            break
    pls = [p for p in pls if ch["scope"] == "cfa" or PL_KEEP.search(p["snippet"]["title"])][:250]
    playlists = []
    for p in pls:
        pids = playlist_ids(p["id"], 500)
        missing = [i for i in pids if i not in meta]
        meta.update(video_meta(missing))
        playlists.append({"id": p["id"], "title": p["snippet"]["title"], "videos": [slim(meta[i]) for i in pids if i in meta]})
    st = it.get("statistics", {})
    dest.write_text(json.dumps({"source": "api", "channel": it["snippet"]["title"], "channel_id": ch["id"],
                                "channel_follower_count": int(st["subscriberCount"]) if st.get("subscriberCount") else None,
                                "uploader_id": it["snippet"].get("customUrl"), "description": "", **ch,
                                "videos": [slim(meta[i]) for i in ids if i in meta], "playlists": playlists}))
    print(f"{ch['name']}: {len(ids)} videos, {len(playlists)} playlists ({units} units used)", flush=True)


def cmd_channels(force):
    (RAW / "channels").mkdir(parents=True, exist_ok=True)
    for ch in json.loads((ROOT / "pipeline" / "channels.json").read_text()):
        fetch_channel(ch, force)


def cmd_refresh():
    """Refresh metadata of videos already in the library; never adds new videos."""
    files = sorted((RAW / "channels").glob("*.json"))
    ids = set()
    for f in files:
        d = json.loads(f.read_text())
        ids |= {v["id"] for v in d["videos"]} | {v["id"] for p in d["playlists"] for v in p["videos"]}
    extra = [RAW / "reddit_videos_meta.jsonl", RAW / "interviews_search.jsonl"]
    for f in extra:
        if f.exists():
            ids |= {json.loads(l)["id"] for l in f.open() if l.strip()}
    fresh = video_meta(sorted(ids))
    for f in files:
        d = json.loads(f.read_text())
        d["videos"] = [{**v, **slim(fresh[v["id"]])} for v in d["videos"] if v["id"] in fresh]
        for p in d["playlists"]:
            p["videos"] = [{**v, **slim(fresh[v["id"]])} for v in p["videos"] if v["id"] in fresh]
        f.write_text(json.dumps(d))
    for f in extra:
        if f.exists():
            rows = [json.loads(l) for l in f.open() if l.strip()]
            f.write_text("".join(json.dumps({**r, **slim(fresh[r["id"]])}) + "\n" for r in rows if r["id"] in fresh))
    print(f"refreshed {len(fresh)} of {len(ids)} videos; {len(ids) - len(fresh)} removed as deleted or private ({units} units used)", flush=True)


def cmd_reddit():
    known = set()
    for f in (RAW / "channels").glob("*.json"):
        d = json.loads(f.read_text())
        known |= {v["id"] for v in d["videos"]}
    want = set()
    for f in RAW.glob("reddit_*_*_*.jsonl"):
        for line in f.open():
            want |= set(json.loads(line)["videos"])
    meta = video_meta(sorted(want - known))
    with (RAW / "reddit_videos_meta.jsonl").open("w") as out:
        for m in meta.values():
            out.write(json.dumps(m) + "\n")
    print(f"Reddit videos: {len(meta)} with metadata ({units} units used)", flush=True)


def cmd_interviews(force=False):
    figs = json.loads((ROOT / "pipeline" / "figures.json").read_text())
    path = RAW / "interviews_search.jsonl"
    rows = [json.loads(l) for l in path.open() if '"api": true' in l] if path.exists() else []
    if force and rows:
        fresh = video_meta([r["id"] for r in rows])
        rows = [{**slim(fresh[r["id"]]), "channel": fresh[r["id"]]["channel"], "channel_id": fresh[r["id"]]["channel_id"],
                 "figure": r["figure"], "api": True} for r in rows if r["id"] in fresh]
        print(f"refreshed metadata for {len(rows)} interview videos ({units} units used)", flush=True)
    done = {r["figure"] for r in rows}
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
        for name, _, _ in figs:
            if name in done:
                continue
            d = call("search", cost=100, part="snippet", q=f"{name} interview", type="video", maxResults=50)
            ids = [it["id"]["videoId"] for it in (d or {}).get("items", [])]
            for m in video_meta(ids).values():
                f.write(json.dumps({**slim(m), "channel": m["channel"], "channel_id": m["channel_id"], "figure": name, "api": True}) + "\n")
            f.flush()
            print(f"{name}: {len(ids)} ({units} units used)", flush=True)


if __name__ == "__main__":
    if not KEY:
        sys.exit("YOUTUBE_API_KEY is not set. Add it in your terminal first (see the instructions in the chat).")
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    force = "--force" in sys.argv
    try:
        if what == "refresh":
            cmd_refresh()
        if what in ("channels", "all"):
            cmd_channels(force)
        if what in ("reddit", "all"):
            cmd_reddit()
        if what in ("interviews", "all"):
            cmd_interviews(force)
    except QuotaExceeded:
        sys.exit(f"Daily YouTube API quota used up after {units} units. Run the same command again tomorrow; finished channels are skipped.")
    print(f"DONE ({units} units used)", flush=True)
