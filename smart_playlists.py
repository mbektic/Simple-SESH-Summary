import json
import logging
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import List, Dict, Any


def _normalize_entry(e: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw Spotify SESH entry to a common shape.
    Only uses local data; no external API calls.
    """
    ts_raw = e.get("ts")
    try:
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else None
    except Exception:
        ts = None
    artist = e.get("master_metadata_album_artist_name") or e.get("artist_name") or "Unknown Artist"
    track = e.get("master_metadata_track_name") or e.get("track_name") or "Unknown Track"
    album = e.get("master_metadata_album_album_name") or e.get("album_name") or "Unknown Album"
    uri = e.get("spotify_track_uri")  # may be None in some exports
    ms = int(e.get("ms_played") or 0)
    skipped = bool(e.get("skipped"))
    return {
        "ts": ts,
        "artist": artist,
        "track": track,
        "album": album,
        "uri": uri,
        "ms": ms,
        "skipped": skipped,
    }


def _dedupe_keep_best(tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate by URI if present else by track+artist, keep the one with max ms."""
    best: Dict[str, Dict[str, Any]] = {}
    for t in tracks:
        key = t.get("uri") or (t.get("track", "") + "|" + t.get("artist", ""))
        prev = best.get(key)
        if not prev or (t.get("ms", 0) > prev.get("ms", 0)):
            best[key] = t
    return list(best.values())


def _clip(tracks: List[Dict[str, Any]], max_n: int) -> List[Dict[str, Any]]:
    return tracks[:max(0, int(max_n))]


def _with_rationale(t: Dict[str, Any], why: str) -> Dict[str, Any]:
    return {
        "track": t.get("track"),
        "artist": t.get("artist"),
        "album": t.get("album"),
        "uri": t.get("uri"),
        "ms_played_sample": t.get("ms", 0),
        "why": why,
    }


def _first_year_seen_by_track(entries: List[Dict[str, Any]]) -> Dict[str, int]:
    first_year: Dict[str, int] = {}
    for e in entries:
        key = (e.get("uri") or (e.get("track", "") + "|" + e.get("artist", "")))
        ts: datetime | None = e.get("ts")
        if not ts:
            continue
        y = ts.year
        if key not in first_year or y < first_year[key]:
            first_year[key] = y
    return first_year


def _artist_play_counts(entries: List[Dict[str, Any]]) -> Counter:
    c = Counter()
    for e in entries:
        if e.get("ms", 0) > 0:
            c[e.get("artist")] += e.get("ms", 0)
    return c


def generate_smart_playlists(raw_entries: List[Dict[str, Any]], max_tracks: int = 50, min_year: int | None = None) -> Dict[str, Any]:
    """
    Build several smart playlist recipes using only local history. Returns a JSON‑serializable dict.
    Each playlist contains items with optional Spotify URIs (when present in the history) and a short rationale.
    """
    try:
        entries = [_normalize_entry(e) for e in raw_entries if int(e.get("ms_played") or 0) > 0]
        # Respect min_year setting, if provided
        if min_year is not None:
            entries = [e for e in entries if e.get("ts") and e["ts"].year >= int(min_year)]
        if not entries:
            return {"playlists": []}

        # Helper maps
        first_year_by_track = _first_year_seen_by_track(entries)
        artist_ms = _artist_play_counts(entries)

        # Index by track key for stats
        per_track: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"plays": 0, "ms": 0, "skips": 0, "sample": None})
        for e in entries:
            key = e.get("uri") or (e.get("track") + "|" + e.get("artist"))
            d = per_track[key]
            d["plays"] += 1
            d["ms"] += e.get("ms", 0)
            if e.get("skipped"):
                d["skips"] += 1
            if not d["sample"] or e.get("ms", 0) > d["sample"].get("ms", 0):
                d["sample"] = e

        # 1) Sunday Evening Wind‑down: Sunday 6pm–11:59pm, sort by average ms per play desc
        sunday_tracks: List[Dict[str, Any]] = []
        for key, stats in per_track.items():
            e = stats["sample"]
            if not e or not e.get("ts"):
                continue
            # Check if any occurrence fell on Sunday evening
            # Simplification: use the best sample's timestamp window
            dt = e["ts"]
            if dt.weekday() == 6 and 18 <= dt.hour <= 23:  # Sunday is 6 (Mon=0)
                avg_ms = stats["ms"] / max(1, stats["plays"])
                sunday_tracks.append((_with_rationale(e, "Played on Sunday evening; high average engagement"), avg_ms))
        sunday_tracks.sort(key=lambda x: x[1], reverse=True)
        sunday_list = [t for t, _ in sunday_tracks]
        sunday_list = _clip(_dedupe_keep_best(sunday_list), max_tracks)

        # 2) High‑Focus Mix: tracks with long average play and low skip rate
        focus_candidates: List[tuple[Dict[str, Any], float]] = []
        for key, stats in per_track.items():
            e = stats["sample"]
            if not e:
                continue
            avg_ms = stats["ms"] / max(1, stats["plays"])
            skip_rate = stats["skips"] / max(1, stats["plays"])
            if avg_ms >= 180000 and skip_rate <= 0.15:
                focus_candidates.append((_with_rationale(e, "Low skip‑rate and long average playtime"), avg_ms))
        focus_candidates.sort(key=lambda x: x[1], reverse=True)
        focus_list = [t for t, _ in focus_candidates]
        focus_list = _clip(_dedupe_keep_best(focus_list), max_tracks)

        # 3) Rediscover YEAR(S): generate a playlist per qualifying year with enough tracks
        year_counts = Counter(first_year_by_track.values())
        qualifying_years = [y for y, cnt in sorted(year_counts.items()) if cnt >= 10]
        # Enforce min_year, if set
        if min_year is not None:
            qualifying_years = [y for y in qualifying_years if y >= int(min_year)]
        # Limit to a reasonable number of years to avoid clutter
        # Prefer older-to-newer order here; UI sorts as provided
        qualifying_years = qualifying_years[:8]
        rediscover_playlists: List[Dict[str, Any]] = []
        for y in qualifying_years:
            tmp: List[tuple[Dict[str, Any], int]] = []
            for key, y0 in first_year_by_track.items():
                if y0 == y:
                    e = per_track[key]["sample"]
                    if e:
                        tmp.append((_with_rationale(e, f"First discovered in {y}"), per_track[key]["plays"]))
            if not tmp:
                continue
            tmp.sort(key=lambda x: x[1], reverse=True)
            year_list = [t for t, _ in tmp]
            year_list = _clip(_dedupe_keep_best(year_list), max_tracks)
            if year_list:
                rediscover_playlists.append({
                    "name": f"Rediscover {y}",
                    "description": f"Bring back favorites first discovered in {y}.",
                    "items": year_list,
                })

        # 4) Deep Cuts from Top Artists: diversify across artists using round‑robin selection
        top_artists = [a for a, _ in artist_ms.most_common(10)]
        deep_cuts: List[Dict[str, Any]] = []
        # Build per-artist candidates, skipping most‑played songs for that artist
        artist_track_counts: Dict[str, List[tuple[str, int]]] = defaultdict(list)
        key_to_track = {}
        for key, stats in per_track.items():
            e = stats["sample"]
            if not e:
                continue
            artist = e.get("artist")
            artist_track_counts[artist].append((key, stats["plays"]))
            key_to_track[key] = e
        per_artist_candidates: Dict[str, List[str]] = {}
        for artist in top_artists:
            ranked = sorted(artist_track_counts.get(artist, []), key=lambda x: x[1], reverse=True)
            # Deep cuts: skip top 2 by plays, include next ones with 1–3 plays
            candidates = [key for key, plays in ranked[2:] if plays <= 3]
            per_artist_candidates[artist] = candidates
        # Round‑robin pick with per‑artist cap
        per_artist_cap = 3
        added_per_artist: Dict[str, int] = defaultdict(int)
        while len(deep_cuts) < max_tracks:
            progressed = False
            for artist in top_artists:
                if added_per_artist[artist] >= per_artist_cap:
                    continue
                lst = per_artist_candidates.get(artist) or []
                if not lst:
                    continue
                key = lst.pop(0)
                e = key_to_track.get(key)
                if not e:
                    continue
                deep_cuts.append(_with_rationale(e, f"Deep cut from a favorite artist: {artist}"))
                added_per_artist[artist] += 1
                progressed = True
                if len(deep_cuts) >= max_tracks:
                    break
            if not progressed:
                break
        deep_cuts = _clip(_dedupe_keep_best(deep_cuts), max_tracks)

        # 5) New Artist Sampler: artists first heard in last 90 days
        now = max((e["ts"] for e in entries if e.get("ts")), default=datetime.utcnow())
        cutoff = now - timedelta(days=90)
        artist_first_seen: Dict[str, datetime] = {}
        for e in entries:
            a = e.get("artist")
            ts = e.get("ts")
            if not ts:
                continue
            if a not in artist_first_seen or ts < artist_first_seen[a]:
                artist_first_seen[a] = ts
        nas: List[Dict[str, Any]] = []
        for a, first_ts in artist_first_seen.items():
            if first_ts >= cutoff:
                # Pick best sample for this artist
                best = None
                for e in entries:
                    if e.get("artist") == a:
                        if not best or e.get("ms", 0) > best.get("ms", 0):
                            best = e
                if best:
                    nas.append(_with_rationale(best, "New artist you discovered recently"))
        nas = _clip(_dedupe_keep_best(nas), max_tracks)

        # 6) Most Skipped Redemption: tracks with skips but also substantial total ms
        redemption: List[tuple[Dict[str, Any], float]] = []
        for key, stats in per_track.items():
            if stats["skips"] >= 1 and stats["ms"] >= 120000:  # at least 2 min total engagement
                e = stats["sample"]
                if e:
                    score = stats["ms"] / (1 + stats["skips"])  # favor those you still listened to
                    redemption.append((_with_rationale(e, "Give it another chance – mixed history (skipped sometimes)"), score))
        redemption.sort(key=lambda x: x[1], reverse=True)
        redemption_list = [t for t, _ in redemption]
        redemption_list = _clip(_dedupe_keep_best(redemption_list), max_tracks)

        playlists = []
        if sunday_list:
            playlists.append({
                "name": "Sunday Evening Wind‑down",
                "description": "Laid‑back tracks you tended to play on Sunday evenings.",
                "items": sunday_list,
            })
        if focus_list:
            playlists.append({
                "name": "High‑Focus Mix",
                "description": "Low skip‑rate, longer‑engagement tracks for concentration.",
                "items": focus_list,
            })
        # Add any Rediscover playlists (multiple years)
        for pl in rediscover_playlists:
            playlists.append(pl)
        if deep_cuts:
            playlists.append({
                "name": "Deep Cuts from Top Artists",
                "description": "Lesser‑played tracks from your most‑played artists.",
                "items": deep_cuts,
            })
        if nas:
            playlists.append({
                "name": "New Artist Sampler",
                "description": "One standout track from artists you discovered recently.",
                "items": nas,
            })
        if redemption_list:
            playlists.append({
                "name": "Most Skipped – Redemption",
                "description": "Tracks you sometimes skipped but still gave a chance.",
                "items": redemption_list,
            })

        return {"generated_at": datetime.utcnow().isoformat() + "Z", "playlists": playlists}
    except Exception as e:
        logging.error(f"Error generating smart playlists: {e}")
        return {"playlists": []}


def write_playlists_to_file(playlists: Dict[str, Any], output_json_path: str) -> None:
    try:
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(playlists, f, ensure_ascii=False, indent=2)
        logging.info(f"✅ Smart playlists exported: {output_json_path}")
    except Exception as e:
        logging.error(f"Failed to write smart playlists to {output_json_path}: {e}")
        raise
