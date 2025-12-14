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
        per_track: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "plays": 0,
            "ms": 0,
            "skips": 0,
            "sample": None,
            "first_ts": None,
            "last_ts": None,
            # For City Skyline Shuffle
            "commute_days": set(),  # set[str YYYY-MM-DD]
            # For Late-Bloomers
            "quarter_counts": defaultdict(int),  # key: (year, q)
        })
        # For recent vs past comparisons
        now_global = max((e.get("ts") for e in entries if e.get("ts")), default=datetime.utcnow())
        last_30_cutoff = now_global - timedelta(days=30)
        last_60_cutoff = now_global - timedelta(days=60)
        last_90_cutoff = now_global - timedelta(days=90)
        last_120_cutoff = now_global - timedelta(days=120)
        per_track_recent_30: Dict[str, int] = defaultdict(int)
        per_track_past_before_30: Dict[str, int] = defaultdict(int)
        for e in entries:
            key = e.get("uri") or (e.get("track") + "|" + e.get("artist"))
            d = per_track[key]
            d["plays"] += 1
            d["ms"] += e.get("ms", 0)
            if e.get("skipped"):
                d["skips"] += 1
            if not d["sample"] or e.get("ms", 0) > d["sample"].get("ms", 0):
                d["sample"] = e
            ts = e.get("ts")
            if ts:
                d["first_ts"] = min(d["first_ts"], ts) if d["first_ts"] else ts
                d["last_ts"] = max(d["last_ts"], ts) if d["last_ts"] else ts
                # Commute windows (7–9am and 4–6pm local time)
                try:
                    if (7 <= ts.hour <= 9) or (16 <= ts.hour <= 18):
                        d["commute_days"].add(ts.date().isoformat())
                except Exception:
                    pass
                # Track per-quarter counts for Late-Bloomers
                try:
                    q = (ts.month - 1) // 3 + 1
                    d["quarter_counts"][(ts.year, q)] += 1
                except Exception:
                    pass

                if ts >= last_30_cutoff:
                    per_track_recent_30[key] += 1
                else:
                    per_track_past_before_30[key] += 1

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
        now = now_global
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

        # 7) Morning Boost: tracks you tended to play in the morning (06:00-09:59)
        morning: List[tuple[Dict[str, Any], float]] = []
        for key, stats in per_track.items():
            e = stats["sample"]
            if not e or not e.get("ts"):
                continue
            dt = e["ts"]
            if 6 <= dt.hour <= 9:
                avg_ms = stats["ms"] / max(1, stats["plays"])
                morning.append((_with_rationale(e, "Frequently played in the morning"), avg_ms))
        morning.sort(key=lambda x: x[1], reverse=True)
        morning_list = _clip(_dedupe_keep_best([t for t, _ in morning]), max_tracks)

        # 8) Night Owl Mix: tracks you tended to play late night (00:00-03:59)
        night: List[tuple[Dict[str, Any], float]] = []
        for key, stats in per_track.items():
            e = stats["sample"]
            if not e or not e.get("ts"):
                continue
            dt = e["ts"]
            if 0 <= dt.hour <= 3:
                avg_ms = stats["ms"] / max(1, stats["plays"])
                night.append((_with_rationale(e, "Your late-night vibe"), avg_ms))
        night.sort(key=lambda x: x[1], reverse=True)
        night_list = _clip(_dedupe_keep_best([t for t, _ in night]), max_tracks)

        # 9) Weekend Bangers: tracks you played on the weekend (Sat/Sun)
        weekend: List[tuple[Dict[str, Any], float]] = []
        for key, stats in per_track.items():
            e = stats["sample"]
            if not e or not e.get("ts"):
                continue
            dt = e["ts"]
            if dt.weekday() in (5, 6):  # Sat=5, Sun=6
                score = stats["plays"] + stats["ms"] / 180000  # blend usage
                weekend.append((_with_rationale(e, "A weekend favorite"), score))
        weekend.sort(key=lambda x: x[1], reverse=True)
        weekend_list = _clip(_dedupe_keep_best([t for t, _ in weekend]), max_tracks)

        # 10) Weekday Flow: tracks you played on weekdays (Mon-Fri)
        weekday: List[tuple[Dict[str, Any], float]] = []
        for key, stats in per_track.items():
            e = stats["sample"]
            if not e or not e.get("ts"):
                continue
            dt = e["ts"]
            if dt.weekday() in (0, 1, 2, 3, 4):
                score = (stats["ms"] / max(1, stats["plays"]))
                weekday.append((_with_rationale(e, "Your weekday go-to"), score))
        weekday.sort(key=lambda x: x[1], reverse=True)
        weekday_list = _clip(_dedupe_keep_best([t for t, _ in weekday]), max_tracks)

        # 11) Forgotten Favorites: high historical use, not played recently (>=120 days)
        forgotten: List[tuple[Dict[str, Any], float]] = []
        for key, stats in per_track.items():
            last_ts = stats.get("last_ts")
            if last_ts and last_ts < last_120_cutoff and stats["ms"] >= 180000:  # 3+ min total
                e = stats["sample"]
                if e:
                    forgotten.append((_with_rationale(e, "Loved before, not heard in a while"), stats["ms"]))
        forgotten.sort(key=lambda x: x[1], reverse=True)
        forgotten_list = _clip(_dedupe_keep_best([t for t, _ in forgotten]), max_tracks)

        # 12) City Skyline Shuffle: commute-hour clustering across many different days
        city_candidates: List[tuple[Dict[str, Any], float]] = []
        for key, stats in per_track.items():
            e = stats.get("sample")
            if not e:
                continue
            days = len(stats.get("commute_days", set()))
            if days < 2:
                continue  # require appearances on multiple days
            avg_ms = stats["ms"] / max(1, stats["plays"])
            # Prefer medium-length engagement; exclude very long-form
            if avg_ms < 90000 or avg_ms > 240000:
                continue
            # Score: favor more distinct days, slight preference toward ~2.5 min
            score = days * 10 - abs(avg_ms - 150000) / 60000.0
            city_candidates.append((_with_rationale(e, "A commute-time staple across days"), score))
        city_candidates.sort(key=lambda x: x[1], reverse=True)
        city_raw = [t for t, _ in city_candidates]
        city_list: List[Dict[str, Any]] = []
        per_artist_added_city: Dict[str, int] = defaultdict(int)
        city_cap = 3
        for item in city_raw:
            artist = item.get("artist")
            if per_artist_added_city[artist] >= city_cap:
                continue
            city_list.append(item)
            per_artist_added_city[artist] += 1
            if len(city_list) >= max_tracks:
                break
        city_list = _clip(_dedupe_keep_best(city_list), max_tracks)

        # 13) Late‑Bloomers: slow-burn increase across quarters
        late_candidates: List[tuple[Dict[str, Any], float]] = []
        for key, stats in per_track.items():
            e = stats.get("sample")
            if not e:
                continue
            qc = stats.get("quarter_counts", {})
            if not qc:
                continue
            # Sort quarters chronologically
            series = sorted(qc.items(), key=lambda x: (x[0][0], x[0][1]))
            counts = [c for (_k, c) in series]
            if sum(counts) < 3 or len(counts) < 3:
                continue
            # Simple linear trend using last up to 6 quarters
            tail = counts[-6:]
            n = len(tail)
            xs = list(range(n))
            mean_x = sum(xs) / n
            mean_y = sum(tail) / n
            num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, tail))
            den = sum((x - mean_x) ** 2 for x in xs) or 1.0
            slope = num / den
            # Require positive slope and the last quarter >= previous
            if slope <= 0 or (n >= 2 and tail[-1] < tail[-2]):
                continue
            score = slope * (sum(tail))
            late_candidates.append((_with_rationale(e, "A slow‑burn favorite rising over time"), score))
        late_candidates.sort(key=lambda x: x[1], reverse=True)
        late_raw = [t for t, _ in late_candidates]
        late_list: List[Dict[str, Any]] = []
        per_artist_added_late: Dict[str, int] = defaultdict(int)
        late_cap = 3
        for item in late_raw:
            artist = item.get("artist")
            if per_artist_added_late[artist] >= late_cap:
                continue
            late_list.append(item)
            per_artist_added_late[artist] += 1
            if len(late_list) >= max_tracks:
                break
        late_list = _clip(_dedupe_keep_best(late_list), max_tracks)

        # 14) One‑Hit Wonder Gems: artists with exactly one track in your history
        artist_track_keys: Dict[str, set] = defaultdict(set)
        for key, stats in per_track.items():
            e = stats["sample"]
            if not e:
                continue
            artist_track_keys[e.get("artist")].add(key)
        ohw: List[tuple[Dict[str, Any], float]] = []
        for artist, keys in artist_track_keys.items():
            if len(keys) == 1:
                k = next(iter(keys))
                s = per_track[k]
                if s.get("sample"):
                    ohw.append((_with_rationale(s["sample"], f"Only track from {artist} you listened to"), s["ms"]))
        ohw.sort(key=lambda x: x[1], reverse=True)
        one_hit_list = _clip(_dedupe_keep_best([t for t, _ in ohw]), max_tracks)

        # 15) Zero‑Skip Keepers: many plays, zero skips
        keepers: List[tuple[Dict[str, Any], float]] = []
        for key, stats in per_track.items():
            if stats["skips"] == 0 and stats["plays"] >= 3:
                e = stats["sample"]
                if e:
                    keepers.append((_with_rationale(e, "Never skipped; always a keeper"), stats["ms"]))
        keepers.sort(key=lambda x: x[1], reverse=True)
        zero_skip_list = _clip(_dedupe_keep_best([t for t, _ in keepers]), max_tracks)

        # 16) Quick Hits: short-and-sweet based on lower average ms per play
        quick: List[tuple[Dict[str, Any], float]] = []
        for key, stats in per_track.items():
            avg_ms = stats["ms"] / max(1, stats["plays"])
            if stats["plays"] >= 2 and avg_ms <= 120000:  # <= 2 minutes on average
                e = stats["sample"]
                if e:
                    quick.append((_with_rationale(e, "Quick hit – bite‑sized plays"), avg_ms))
        quick.sort(key=lambda x: x[1])  # shortest first
        quick_hits_list = _clip(_dedupe_keep_best([t for t, _ in quick]), max_tracks)

        # 17) Seasonal Echoes: tracks with a history of appearing in the current month (across years)
        # Build per-track engagement that happened in the current calendar month (any year)
        seasonal_scores: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"ms": 0, "plays": 0})
        current_month = now_global.month
        for e in entries:
            ts = e.get("ts")
            if not ts:
                continue
            if ts.month == current_month:
                key = e.get("uri") or (e.get("track") + "|" + e.get("artist"))
                s = seasonal_scores[key]
                s["ms"] += e.get("ms", 0)
                s["plays"] += 1
        seasonal_rank: List[tuple[str, float]] = []
        for key, s in seasonal_scores.items():
            if s["plays"] >= 2 or s["ms"] >= 120000:  # at least some meaningful recurrence within this month across years
                # score favors consistent engagement within this month
                score = s["ms"] + 30000 * (s["plays"] - 1)
                seasonal_rank.append((key, score))
        seasonal_rank.sort(key=lambda x: x[1], reverse=True)
        seasonal_list: List[Dict[str, Any]] = []
        month_name = now_global.strftime("%B")
        for key, _ in seasonal_rank:
            e = per_track.get(key, {}).get("sample")
            if e:
                seasonal_list.append(_with_rationale(e, f"A {month_name} favorite across years"))
            if len(seasonal_list) >= max_tracks:
                break
        seasonal_list = _clip(_dedupe_keep_best(seasonal_list), max_tracks)

        # 17) Fresh Repeat Offenders: first heard in last 60 days, played 3+ times total
        fresh_repeat: List[tuple[Dict[str, Any], float]] = []
        for key, stats in per_track.items():
            first_ts = stats.get("first_ts")
            if first_ts and first_ts >= last_60_cutoff and stats["plays"] >= 3:
                e = stats["sample"]
                if e:
                    fresh_repeat.append((_with_rationale(e, "New but already repeat‑worthy"), stats["plays"]))
        fresh_repeat.sort(key=lambda x: x[1], reverse=True)
        fresh_repeat_raw = [t for t, _ in fresh_repeat]
        # Enforce per-artist cap of 5 to avoid concentration
        fresh_repeat_list: List[Dict[str, Any]] = []
        cap = 5
        per_artist_added: Dict[str, int] = defaultdict(int)
        for item in fresh_repeat_raw:
            artist = item.get("artist")
            if per_artist_added[artist] >= cap:
                continue
            fresh_repeat_list.append(item)
            per_artist_added[artist] += 1
            if len(fresh_repeat_list) >= max_tracks:
                break
        fresh_repeat_list = _clip(_dedupe_keep_best(fresh_repeat_list), max_tracks)

        # 18) Artist Variety Sampler: one strong pick per many different artists
        artist_best: List[tuple[Dict[str, Any], float]] = []
        seen_artist: set = set()
        # Rank keys by artist total ms, then pick each artist's top track
        for artist, total_ms in artist_ms.most_common(100):
            # find best sample for artist
            best_e = None
            best_score = -1.0
            for key, stats in per_track.items():
                e = stats["sample"]
                if e and e.get("artist") == artist:
                    score = stats["ms"]  # total engagement
                    if score > best_score:
                        best_score = score
                        best_e = e
            if best_e and artist not in seen_artist:
                seen_artist.add(artist)
                artist_best.append((_with_rationale(best_e, f"Representative pick from {artist}"), best_score))
            if len(artist_best) >= max_tracks * 2:
                break
        # sort by artist strength but keep diversity
        artist_best.sort(key=lambda x: x[1], reverse=True)
        artist_variety_list = _clip(_dedupe_keep_best([t for t, _ in artist_best]), max_tracks)

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
        if morning_list:
            playlists.append({
                "name": "Morning Boost",
                "description": "Your most morning‑friendly plays (6–10am).",
                "items": morning_list,
            })
        if night_list:
            playlists.append({
                "name": "Night Owl Mix",
                "description": "Late‑night listens between midnight and 4am.",
                "items": night_list,
            })
        if weekend_list:
            playlists.append({
                "name": "Weekend Bangers",
                "description": "Songs you gravitate to on Saturdays and Sundays.",
                "items": weekend_list,
            })
        if weekday_list:
            playlists.append({
                "name": "Weekday Flow",
                "description": "Reliable weekday companions for work or study.",
                "items": weekday_list,
            })
        if forgotten_list:
            playlists.append({
                "name": "Forgotten Favorites",
                "description": "Bring back tracks you loved but haven’t played lately.",
                "items": forgotten_list,
            })
        if city_list:
            playlists.append({
                "name": "City Skyline Shuffle",
                "description": "Commute‑hour staples across different days – mid‑length, easy flow.",
                "items": city_list,
            })
        if late_list:
            playlists.append({
                "name": "Late‑Bloomers",
                "description": "Slow‑burn risers across quarters – getting better with time.",
                "items": late_list,
            })
        if one_hit_list:
            playlists.append({
                "name": "One‑Hit Wonder Gems",
                "description": "Great songs from artists you only played once in your history.",
                "items": one_hit_list,
            })
        if zero_skip_list:
            playlists.append({
                "name": "Zero‑Skip Keepers",
                "description": "Often played and never skipped – certified keepers.",
                "items": zero_skip_list,
            })
        if quick_hits_list:
            playlists.append({
                "name": "Quick Hits",
                "description": "Short and snappy – quick listens you return to.",
                "items": quick_hits_list,
            })
        if seasonal_list:
            playlists.append({
                "name": "Seasonal Echoes",
                "description": "Tracks you gravitate to this month across the years.",
                "items": seasonal_list,
            })
        if fresh_repeat_list:
            playlists.append({
                "name": "Fresh Repeat Offenders",
                "description": "New discoveries you already replay a lot.",
                "items": fresh_repeat_list,
            })
        if artist_variety_list:
            playlists.append({
                "name": "Artist Variety Sampler",
                "description": "One strong pick from many of your favorite artists.",
                "items": artist_variety_list,
            })

        # Sort playlists alphabetically by name before returning
        try:
            playlists.sort(key=lambda p: (p.get("name") or "").casefold())
        except Exception:
            # Fallback: simple string sort without casefold if any unexpected types
            playlists.sort(key=lambda p: str(p.get("name") or ""))

        return {"generated_at": datetime.utcnow().isoformat() + "Z", "playlists": playlists}
    except Exception as e:
        logging.error(f"Error generating smart playlists: {e}")
        return {"playlists": []}