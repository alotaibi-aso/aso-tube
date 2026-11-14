"""Rebuild data/raw from the published videos.json (which itself came from the YouTube API).

Lets an incremental run fetch only channels that are not published yet, instead of
spending a full day's quota. Interviews found by search are restored too, so no
search calls are needed.
"""
import json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = Path(os.environ.get("ASO_RAW", ROOT / "data" / "raw"))
pub = json.loads((ROOT / "videos.json").read_text())
curated = {c["id"]: c for c in json.loads((ROOT / "pipeline" / "channels.json").read_text())}
figures = [f[0] for f in pub.get("figures", [])]

chans = pub["channels"]
by_ch = {}
for r in pub["videos"]:
    by_ch.setdefault(r[2], []).append(r)


def vid(r):
    out = {"id": r[0], "title": r[1]}
    if r[3]:
        out["duration"] = r[3]
    if r[4]:
        out["view_count"] = r[4]
    if r[5]:
        out["timestamp"] = r[5]
    return out


(RAW / "channels").mkdir(parents=True, exist_ok=True)
seeded = 0
for i, (cid, name, handle, subs, tier, scope, r, nv) in enumerate(chans):
    if cid not in curated or scope != curated[cid]["scope"]:
        continue
    rows = by_ch.get(i, [])
    pls = [{"id": p[0], "title": p[1], "videos": [vid(pub["videos"][j]) for j in p[6]]} for p in pub["playlists"] if p[2] == i]
    (RAW / "channels" / f"{cid}.json").write_text(json.dumps({
        "source": "api", "channel": name, "channel_id": cid, "channel_follower_count": subs or None,
        "uploader_id": handle or None, "description": "", **curated[cid],
        "videos": [vid(x) for x in rows], "playlists": pls}))
    seeded += 1

iv = 0
with (RAW / "interviews_search.jsonl").open("w") as f:
    for r in pub["videos"]:
        if len(r) > 12 and r[12] and chans[r[2]][5] == "iv":
            f.write(json.dumps({**vid(r), "channel": chans[r[2]][1], "channel_id": chans[r[2]][0],
                                "figure": figures[r[12] - 1], "api": True}) + "\n")
            iv += 1
print(f"seeded {seeded} channels and {iv} interviews from the published data", flush=True)
