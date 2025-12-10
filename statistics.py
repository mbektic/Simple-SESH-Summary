"""
Statistics calculation module for Spotify Extended Streaming History.

This module contains functions for calculating various statistics from
Spotify Extended Streaming History data.
"""
import calendar
import logging
from collections import Counter
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Set, DefaultDict

def calculate_basic_stats(
    first_ts: datetime,
    first_entry: Dict[str, Any],
    last_ts: datetime,
    last_entry: Dict[str, Any],
    dates_set: Set[date]
) -> Dict[str, Any]:
    """
    Calculate basic statistics about the listening history.

    Args:
        first_ts: First timestamp
        first_entry: First entry
        last_ts: Last timestamp
        last_entry: Last entry
        dates_set: Set of dates played

    Returns:
        Dict containing basic statistics:
            - days_since_first: Days since first play
            - days_played: Number of days played
            - pct_days: Percentage of days played
            - first_str: First play date as string
            - first_desc: First play description
            - last_str: Last play date as string
            - last_desc: Last play description
    """
    try:
        today = date.today()

        # Handle case where no valid entries were found
        if first_ts is None:
            logging.warning("No valid entries found with timestamps, using default values for stats")
            return {
                "days_since_first": 0,
                "days_played": 0,
                "pct_days": 0,
                "first_str": "N/A",
                "first_desc": "No data available",
                "last_str": "N/A",
                "last_desc": "No data available"
            }

        days_since_first = (today - first_ts.date()).days
        days_played = len(dates_set)
        pct_days = days_played / days_since_first * 100 if days_since_first > 0 else 0

        # Format first entry details with fallbacks for missing data
        first_str = first_ts.strftime("%b %d, %Y")
        first_artist = first_entry.get('master_metadata_album_artist_name', 'Unknown Artist')
        first_track = first_entry.get('master_metadata_track_name', 'Unknown Track')
        first_desc = f"{first_str} ({first_artist} - {first_track})"

        # Format last entry details with fallbacks for missing data
        last_str = last_ts.strftime("%b %d, %Y")
        last_artist = last_entry.get('master_metadata_album_artist_name', 'Unknown Artist')
        last_track = last_entry.get('master_metadata_track_name', 'Unknown Track')
        last_desc = f"{last_str} ({last_artist} - {last_track})"

        return {
            "days_since_first": days_since_first,
            "days_played": days_played,
            "pct_days": pct_days,
            "first_str": first_str,
            "first_desc": first_desc,
            "last_str": last_str,
            "last_desc": last_desc
        }
    except Exception as e:
        logging.error(f"Error computing basic stats: {e}")
        return {
            "days_since_first": 0,
            "days_played": 0,
            "pct_days": 0,
            "first_str": "Error",
            "first_desc": "Error computing stats",
            "last_str": "Error",
            "last_desc": "Error computing stats"
        }

def calculate_library_stats(
    artist_set: Set[str],
    album_set: Set[str],
    track_set: Set[str],
    artist_tracks: DefaultDict[str, Set[str]],
    yearly: DefaultDict[int, Dict[str, DefaultDict[str, int]]]
) -> Dict[str, Any]:
    """
    Calculate statistics about the music library.

    Args:
        artist_set: Set of artists
        album_set: Set of albums
        track_set: Set of tracks
        artist_tracks: Dictionary mapping artists to their tracks
        yearly: Dictionary of yearly statistics

    Returns:
        Dict containing library statistics:
            - artists_count: Number of artists
            - one_hits: Number of one-hit wonders
            - pct_one_hits: Percentage of one-hit wonders
            - every_year_list: List of artists present in every year
            - every_year_count: Number of artists present in every year
            - albums_count: Number of albums
            - albums_per_artist: Average number of albums per artist
            - tracks_count: Number of tracks
    """
    try:
        # Calculate artist statistics with error handling
        artists_count = len(artist_set)
        if artists_count > 0:
            one_hits = sum(1 for a, ts in artist_tracks.items() if len(ts) == 1)
            pct_one_hits = one_hits / artists_count * 100
        else:
            logging.warning("No artists found, using default values for artist stats")
            one_hits = 0
            pct_one_hits = 0

        # Only artists counted in artist_counts (i.e. at least one play > min_milliseconds) in *every* year
        if yearly:
            try:
                year_artist_sets = [
                    set(ydata["artist_counts"].keys())
                    for ydata in yearly.values()
                ]
                if year_artist_sets:
                    every_year_list = sorted(set.intersection(*year_artist_sets))
                    every_year_count = len(every_year_list)
                else:
                    every_year_list = []
                    every_year_count = 0
            except Exception as e:
                logging.error(f"Error computing every-year artists: {e}")
                every_year_list = []
                every_year_count = 0
        else:
            every_year_list = []
            every_year_count = 0

        # Calculate album and track statistics with error handling
        albums_count = len(album_set)
        tracks_count = len(track_set)

        # Avoid division by zero
        if artists_count > 0:
            albums_per_artist = albums_count / artists_count
        else:
            albums_per_artist = 0

        return {
            "artists_count": artists_count,
            "one_hits": one_hits,
            "pct_one_hits": pct_one_hits,
            "every_year_list": every_year_list,
            "every_year_count": every_year_count,
            "albums_count": albums_count,
            "albums_per_artist": albums_per_artist,
            "tracks_count": tracks_count
        }
    except Exception as e:
        logging.error(f"Error computing library stats: {e}")
        return {
            "artists_count": 0,
            "one_hits": 0,
            "pct_one_hits": 0,
            "every_year_list": [],
            "every_year_count": 0,
            "albums_count": 0,
            "albums_per_artist": 0,
            "tracks_count": 0
        }

def calculate_milestone_stats(
    daily_counts: Counter,
    all_data: Dict[str, DefaultDict[str, int]],
    yearly: DefaultDict[int, Dict[str, DefaultDict[str, int]]],
    monthly_counts: Counter
) -> Dict[str, Any]:
    """
    Calculate milestone statistics.

    Args:
        daily_counts: Counter of plays per day
        all_data: Aggregated data for all years
        yearly: Dictionary of yearly statistics
        monthly_counts: Counter of plays per month

    Returns:
        Dict containing milestone statistics:
            - edd: Eddington number
            - next_need: Days needed for next Eddington number
            - art_cut: Artist cut-over point
            - pop_year: Most popular year
            - pop_year_plays: Number of plays in the most popular year
            - pop_mon_str: Most popular month
            - pop_mon_plays: Number of plays in most popular month
            - week_str: Most popular week
            - week_plays: Number of plays in most popular week
            - day_str: Most popular day
            - day_plays: Number of plays in the most popular day
    """
    try:
        # Calculate Eddington number with error handling
        counts = sorted(daily_counts.values(), reverse=True)
        if counts:
            edd = next((i for i, n in enumerate(counts, start=1) if n < i), len(counts))
            next_need = max(0, (edd + 1) - sum(1 for c in counts if c >= edd + 1))
        else:
            logging.warning("No daily counts found, using default values for Eddington number")
            edd = 0
            next_need = 0

        # ─── Artist cut-over point ────────────────────────────────
        try:
            art_vals = sorted(all_data["artist_counts"].values(), reverse=True)
            if art_vals:
                art_cut = next((i for i, n in enumerate(art_vals, start=1) if n < i), len(art_vals))
            else:
                art_cut = 0
        except Exception as e:
            logging.error(f"Error computing artist cut-over point: {e}")
            art_cut = 0

        # ─── Most popular year/month/week/day ─────────────────────────────
        # Most popular year
        try:
            if yearly:
                year_plays = {y: sum(d["track_counts"].values()) for y, d in yearly.items()}
                if year_plays:
                    pop_year, pop_year_plays = max(year_plays.items(), key=lambda kv: kv[1])
                else:
                    pop_year, pop_year_plays = "N/A", 0
            else:
                pop_year, pop_year_plays = "N/A", 0
        except Exception as e:
            logging.error(f"Error computing most popular year: {e}")
            pop_year, pop_year_plays = "N/A", 0

        # Most popular month
        try:
            if monthly_counts:
                (pm_y, pm_m), pop_mon_plays = max(monthly_counts.items(), key=lambda kv: kv[1])
                pop_mon_str = f"{calendar.month_name[pm_m]} {pm_y}"
            else:
                pop_mon_str, pop_mon_plays = "N/A", 0
        except Exception as e:
            logging.error(f"Error computing most popular month: {e}")
            pop_mon_str, pop_mon_plays = "N/A", 0

        # Most popular week
        try:
            weekly_counts = Counter()
            for d, cnt in daily_counts.items():
                yr, wk, _ = d.isocalendar()
                weekly_counts[(yr, wk)] += cnt

            if weekly_counts:
                (wy, ww), week_plays = weekly_counts.most_common(1)[0]
                week_start = datetime.strptime(f"{wy}-W{ww}-1", "%G-W%V-%u").date()
                week_end = week_start + timedelta(days=6)
                week_str = f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"
            else:
                week_str, week_plays = "N/A", 0
        except Exception as e:
            logging.error(f"Error computing most popular week: {e}")
            week_str, week_plays = "N/A", 0

        # — Most popular day (single date) —
        try:
            if daily_counts:
                most_day, day_plays = daily_counts.most_common(1)[0]
                day_str = most_day.strftime("%b %d, %Y")
            else:
                day_str, day_plays = "N/A", 0
        except Exception as e:
            logging.error(f"Error computing most popular day: {e}")
            day_str, day_plays = "N/A", 0

        return {
            "edd": edd,
            "next_need": next_need,
            "art_cut": art_cut,
            "pop_year": pop_year,
            "pop_year_plays": pop_year_plays,
            "pop_mon_str": pop_mon_str,
            "pop_mon_plays": pop_mon_plays,
            "week_str": week_str,
            "week_plays": week_plays,
            "day_str": day_str,
            "day_plays": day_plays
        }
    except Exception as e:
        logging.error(f"Error computing milestone stats: {e}")
        return {
            "edd": 0,
            "next_need": 0,
            "art_cut": 0,
            "pop_year": "N/A",
            "pop_year_plays": 0,
            "pop_mon_str": "N/A",
            "pop_mon_plays": 0,
            "week_str": "N/A",
            "week_plays": 0,
            "day_str": "N/A",
            "day_plays": 0
        }

def calculate_pattern_stats(
    dates_set: Set[date],
    daily_counts: Counter,
    weekday_counts: Counter,
    hour_counts: Counter
) -> Dict[str, Any]:
    """
    Calculate listening pattern statistics.

    Args:
        dates_set: Set of dates played
        daily_counts: Counter of plays per day
        weekday_counts: Counter of plays per weekday
        hour_counts: Counter of plays per hour

    Returns:
        Dict containing pattern statistics:
            - max_streak: Longest listening streak
            - streak_start: Start date of longest streak
            - streak_end: End date of longest streak
            - longest_hiatus: Longest hiatus
            - hi_start_str: Start date of longest hiatus
            - hi_end_str: End date of longest hiatus
            - avg_plays: Average plays per active day
            - wd_name: Most active weekday
            - wd_count: Number of plays on most active weekday
            - peak_hour_str: Peak listening hour
            - hour_count: Number of plays in peak hour
            - weekend: Number of plays on weekends
            - weekday: Number of plays on weekdays
            - ratio_pct: Weekend to weekday ratio percentage
    """
    result = {}

    # — Longest Listening Streak (with date range) —
    try:
        sorted_dates = sorted(dates_set)
        if sorted_dates:
            # initialize
            max_streak = curr_streak = 1
            streak_start = streak_end = sorted_dates[0]
            temp_start = sorted_dates[0]

            for prev_day, next_day in zip(sorted_dates, sorted_dates[1:]):
                if next_day == prev_day + timedelta(days=1):
                    curr_streak += 1
                else:
                    curr_streak = 1
                    temp_start = next_day
                # record a new max
                if curr_streak > max_streak:
                    max_streak = curr_streak
                    streak_start = temp_start
                    streak_end = next_day
        else:
            logging.warning("No dates found, using default values for streak stats")
            max_streak = 0
            streak_start = streak_end = None
    except Exception as e:
        logging.error(f"Error computing listening streak: {e}")
        max_streak = 0
        streak_start = streak_end = None

    result["max_streak"] = max_streak
    result["streak_start"] = streak_start
    result["streak_end"] = streak_end

    # — Average Plays per Active Day —
    try:
        if dates_set:
            avg_plays = sum(daily_counts.values()) / len(dates_set)
        else:
            avg_plays = 0
    except Exception as e:
        logging.error(f"Error computing average plays per day: {e}")
        avg_plays = 0

    result["avg_plays"] = avg_plays

    # — Most Active Weekday —
    try:
        if weekday_counts:
            wd_index, wd_count = weekday_counts.most_common(1)[0]
            wd_name = calendar.day_name[wd_index]
        else:
            wd_name, wd_count = "N/A", 0
    except Exception as e:
        logging.error(f"Error computing most active weekday: {e}")
        wd_name, wd_count = "N/A", 0

    result["wd_name"] = wd_name
    result["wd_count"] = wd_count

    # — Peak Listening Hour —
    try:
        if hour_counts:
            peak_hour, hour_count = hour_counts.most_common(1)[0]
            hour12 = peak_hour % 12 or 12
            suffix = "AM" if peak_hour < 12 else "PM"
            peak_hour_str = f"{hour12}{suffix}"
        else:
            peak_hour_str, hour_count = "N/A", 0
    except Exception as e:
        logging.error(f"Error computing peak listening hour: {e}")
        peak_hour_str, hour_count = "N/A", 0

    result["peak_hour_str"] = peak_hour_str
    result["hour_count"] = hour_count

    # ─── Weekend vs Weekday Ratio ────────────────────────────
    try:
        weekend = weekday_counts[5] + weekday_counts[6]  # Sat=5, Sun=6
        weekday = sum(weekday_counts[i] for i in range(5))
        ratio_pct = weekend / weekday * 100 if weekday else 0
    except Exception as e:
        logging.error(f"Error computing weekend vs weekday ratio: {e}")
        weekend = 0
        weekday = 0
        ratio_pct = 0

    result["weekend"] = weekend
    result["weekday"] = weekday
    result["ratio_pct"] = ratio_pct

    # ─── Longest Hiatus ───────────────────────────────────────
    try:
        longest_hiatus = 0
        hiatus_start = hiatus_end = None

        # Only compute if we have enough dates
        if len(sorted_dates) > 1:
            for prev_day, next_day in zip(sorted_dates, sorted_dates[1:]):
                gap = (next_day - prev_day).days - 1
                if gap > longest_hiatus:
                    longest_hiatus = gap
                    hiatus_start = prev_day + timedelta(days=1)
                    hiatus_end = next_day - timedelta(days=1)

            if longest_hiatus > 0:
                hi_start_str = hiatus_start.strftime("%b %d, %Y")
                hi_end_str = hiatus_end.strftime("%b %d, %Y")
            else:
                hi_start_str = hi_end_str = None
        else:
            hi_start_str = hi_end_str = None
    except Exception as e:
        logging.error(f"Error computing longest hiatus: {e}")
        longest_hiatus = 0
        hi_start_str = hi_end_str = None

    result["longest_hiatus"] = longest_hiatus
    result["hi_start_str"] = hi_start_str
    result["hi_end_str"] = hi_end_str

    return result

def calculate_session_stats(
    play_times: List[datetime],
    play_counted: int,
    skip_count: int,
    offline_count: int
) -> Dict[str, Any]:
    """
    Calculate listening session statistics.

    Args:
        play_times: List of play timestamps
        play_counted: Total number of plays counted
        skip_count: Number of skipped tracks
        offline_count: Number of offline plays

    Returns:
        Dict containing session statistics:
            - num_sessions: Number of listening sessions
            - avg_str: Average session length
            - long_str: Longest single session
            - long_date_str: Date of the longest session
            - skip_count: Number of skipped tracks
            - play_counted: Total number of plays counted
            - skip_rate_pct: Skip rate percentage
            - offline_count: Number of offline plays
            - online_count: Number of online plays
            - offline_ratio_pct: Offline to online ratio percentage
            - ratio_str: Offline to online ratio string
    """
    result = {}

    # ─── Listening session stats ───────────────────────────
    try:
        play_times.sort()
        sessions = []
        if play_times:
            start = prev = play_times[0]
            gap = timedelta(minutes=30)
            for t in play_times[1:]:
                if t - prev > gap:
                    sessions.append((start, prev))
                    start = t
                prev = t
            sessions.append((start, prev))

        num_sessions = len(sessions)
        durations = [(end - start) for start, end in sessions]
        total_dur = sum(durations, timedelta())
        avg_session = total_dur / num_sessions if num_sessions else timedelta()

        if durations:
            # find the longest session and its start
            longest_dur = max(durations)
            idx = durations.index(longest_dur)
            longest_start, longest_end = sessions[idx]
        else:
            longest_dur = timedelta()
            longest_start = longest_end = None

        # format durations
        avg_seconds = int(avg_session.total_seconds())
        avg_hours = avg_seconds // 3600
        avg_minutes = (avg_seconds % 3600) // 60
        avg_seconds = avg_seconds % 60
        avg_str = f"{avg_hours:02}h {avg_minutes:02}m {avg_seconds:02}s"

        long_seconds = int(longest_dur.total_seconds())
        long_hours = long_seconds // 3600
        long_minutes = (long_seconds % 3600) // 60
        long_seconds = long_seconds % 60
        long_str = f"{long_hours:02}h {long_minutes:02}m {long_seconds:02}s"

        # format date for the longest session
        if longest_start:
            long_date_str = longest_start.strftime("%b %d, %Y")
        else:
            long_date_str = "N/A"
    except Exception as e:
        logging.error(f"Error computing listening session stats: {e}")
        num_sessions = 0
        avg_str = "00h 00m 00s"
        long_str = "00h 00m 00s"
        long_date_str = "N/A"

    result["num_sessions"] = num_sessions
    result["avg_str"] = avg_str
    result["long_str"] = long_str
    result["long_date_str"] = long_date_str

    # ─── Skip rate and offline/online ratio ─────────────────────
    try:
        if play_counted > 0:
            online_count = play_counted - offline_count
            skip_rate_pct = (skip_count / play_counted * 100)
            offline_ratio_pct = (offline_count / play_counted * 100)
            ratio_str = f"{offline_count}:{online_count}"
        else:
            online_count = 0
            skip_rate_pct = 0
            offline_ratio_pct = 0
            ratio_str = "0:0"
    except Exception as e:
        logging.error(f"Error computing skip rate and offline ratio: {e}")
        online_count = 0
        skip_rate_pct = 0
        offline_ratio_pct = 0
        ratio_str = "0:0"

    result["skip_count"] = skip_count
    result["play_counted"] = play_counted
    result["skip_rate_pct"] = skip_rate_pct
    result["offline_count"] = offline_count
    result["online_count"] = online_count
    result["offline_ratio_pct"] = offline_ratio_pct
    result["ratio_str"] = ratio_str

    return result

def calculate_track_stats(
    all_data: Dict[str, DefaultDict[str, int]],
    track_set: Set[str],
    track_skip_counts: Counter
) -> Dict[str, Any]:
    """
    Calculate track-related statistics.

    Args:
        all_data: Aggregated data for all years
        track_set: Set of tracks
        track_skip_counts: Counter of skips per track

    Returns:
        Dict containing track statistics:
            - total_ms: Total listening time in milliseconds
            - total_plays: Total number of plays
            - total_time_str: Total listening time as string
            - avg_play_ms: Average playtime in milliseconds
            - avg_play_str: Average playtime as string
            - unique_tracks: Number of unique tracks
            - unique_ratio_pct: Unique tracks ratio percentage
            - most_skipped: Most skipped track
            - skip_ct: Number of skips for most skipped track
            - gini: Gini coefficient of artist plays
    """
    result = {}

    # ─── Total listening time and average per play ─────────────
    try:
        total_ms = sum(all_data["track_time"].values())
        total_plays = sum(all_data["track_counts"].values())

        # Format total time
        total_seconds = total_ms // 1000
        total_hours = total_seconds // 3600
        total_minutes = (total_seconds % 3600) // 60
        total_seconds = total_seconds % 60
        total_time_str = f"{total_hours:02}h {total_minutes:02}m {total_seconds:02}s"

        if total_plays > 0:
            avg_play_ms = total_ms / total_plays

            # Format average playtime
            avg_seconds = int(avg_play_ms) // 1000
            avg_hours = avg_seconds // 3600
            avg_minutes = (avg_seconds % 3600) // 60
            avg_seconds = avg_seconds % 60
            avg_play_str = f"{avg_hours:02}h {avg_minutes:02}m {avg_seconds:02}s"
        else:
            avg_play_ms = 0
            avg_play_str = "00h 00m 00s"
    except Exception as e:
        logging.error(f"Error computing total listening time: {e}")
        total_ms = 0
        total_plays = 0
        total_time_str = "00h 00m 00s"
        avg_play_ms = 0
        avg_play_str = "00h 00m 00s"

    result["total_ms"] = total_ms
    result["total_plays"] = total_plays
    result["total_time_str"] = total_time_str
    result["avg_play_ms"] = avg_play_ms
    result["avg_play_str"] = avg_play_str

    # ─── Unique Tracks Ratio ───────────────────────────────────
    try:
        unique_tracks = len(track_set)
        if total_plays > 0:
            unique_ratio_pct = unique_tracks / total_plays * 100
        else:
            unique_ratio_pct = 0
    except Exception as e:
        logging.error(f"Error computing unique tracks ratio: {e}")
        unique_tracks = 0
        unique_ratio_pct = 0

    result["unique_tracks"] = unique_tracks
    result["unique_ratio_pct"] = unique_ratio_pct

    # ─── Most skipped track ───────────────────────────────────
    try:
        if track_skip_counts:
            most_skipped, skip_ct = track_skip_counts.most_common(1)[0]
        else:
            most_skipped, skip_ct = "N/A", 0
    except Exception as e:
        logging.error(f"Error computing most skipped track: {e}")
        most_skipped, skip_ct = "N/A", 0

    result["most_skipped"] = most_skipped
    result["skip_ct"] = skip_ct

    # ─── Gini Coefficient of Artist Plays ─────────────────────
    try:
        vals = sorted(all_data["artist_counts"].values())
        n = len(vals)
        if n and sum(vals):
            weighted = sum((i + 1) * v for i, v in enumerate(vals))
            gini = (2 * weighted) / (n * sum(vals)) - (n + 1) / n
        else:
            gini = 0
    except Exception as e:
        logging.error(f"Error computing Gini coefficient: {e}")
        gini = 0

    result["gini"] = gini

    return result

def calculate_personality_type(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate the listening personality type based on various statistics.

    Args:
        stats: Dictionary containing statistics

    Returns:
        Dict containing personality type information:
            - personality_type: The primary personality type
            - personality_desc: Description of the personality type
    """
    try:
        # Extract relevant statistics
        unique_ratio = stats.get("unique_ratio_pct", 0)
        gini = stats.get("gini", 0)
        skip_rate = stats.get("skip_rate_pct", 0)
        weekend_ratio = stats.get("ratio_pct", 0)
        artists_count = stats.get("artists_count", 0)
        one_hits_pct = stats.get("pct_one_hits", 0)
        avg_play_ms = stats.get("avg_play_ms", 0)
        total_plays = stats.get("total_plays", 0)
        days_played = stats.get("days_played", 0)
        days_since_first = stats.get("days_since_first", 1)
        max_streak = stats.get("max_streak", 0)
        tracks_count = stats.get("tracks_count", 0)
        albums_count = stats.get("albums_count", 0)

        # Calculate additional metrics
        listening_frequency = days_played / max(1, days_since_first)
        artist_to_track_ratio = artists_count / max(1, tracks_count)
        album_to_artist_ratio = albums_count / max(1, artists_count)
        avg_play_minutes = avg_play_ms / 60000  # Convert to minutes

        # Define thresholds with more granularity
        unique_ratio_thresholds = [30, 50, 70]  # Low, Medium, High
        gini_thresholds = [0.3, 0.5, 0.7]  # Low, Medium, High concentration
        skip_rate_thresholds = [15, 30, 45]  # Low, Medium, High
        weekend_ratio_thresholds = [30, 50, 70]  # Low, Medium, High
        artists_count_thresholds = [50, 100, 200]  # Low, Medium, High
        one_hits_thresholds = [20, 40, 60]  # Low, Medium, High
        listening_frequency_thresholds = [0.3, 0.6, 0.9]  # Low, Medium, High (more challenging)
        avg_play_minutes_thresholds = [2, 3, 4]  # Low, Medium, High
        streak_thresholds = [5, 14, 30]  # Low, Medium, High

        # Helper function to get score based on thresholds
        def get_threshold_score(value, thresholds, reverse=False):
            if reverse:
                if value <= thresholds[0]: return 3
                if value <= thresholds[1]: return 2
                if value <= thresholds[2]: return 1
                return 0
            else:
                if value >= thresholds[2]: return 3
                if value >= thresholds[1]: return 2
                if value >= thresholds[0]: return 1
                return 0

        # Calculate more nuanced scores for each personality type
        scores = {
            "Explorer": (
                get_threshold_score(unique_ratio, unique_ratio_thresholds) * 1.7 +  # Boosted weight
                get_threshold_score(gini, gini_thresholds, reverse=True) * 1.7 +  # Boosted weight
                get_threshold_score(artists_count, artists_count_thresholds) * 1.5 +  # Boosted weight
                get_threshold_score(one_hits_pct, one_hits_thresholds) * 1.2 +  # Boosted weight
                (1.0 if artist_to_track_ratio < 0.3 else 0) +  # Many tracks per artist (boosted)
                (1.5 if unique_ratio > 60 else 0)  # Added: very high unique ratio
            ),
            "Loyalist": (
                get_threshold_score(unique_ratio, unique_ratio_thresholds, reverse=True) * 1.2 +
                get_threshold_score(gini, gini_thresholds) * 1.5 +
                get_threshold_score(artists_count, artists_count_thresholds, reverse=True) * 1.0 +
                (1.0 if album_to_artist_ratio > 1.5 else 0)  # Multiple albums per artist
            ),
            "Eclectic": (
                get_threshold_score(one_hits_pct, one_hits_thresholds) * 1.5 +
                get_threshold_score(artists_count, artists_count_thresholds) * 1.2 +
                get_threshold_score(unique_ratio, unique_ratio_thresholds) * 1.0 +
                (1.0 if artist_to_track_ratio > 0.7 else 0)  # Few tracks per artist
            ),
            "Focused": (
                get_threshold_score(one_hits_pct, one_hits_thresholds, reverse=True) * 1.5 +
                get_threshold_score(gini, gini_thresholds) * 1.2 +
                get_threshold_score(unique_ratio, unique_ratio_thresholds, reverse=True) * 1.0 +
                (1.0 if tracks_count < 200 else 0)  # Limited track selection
            ),
            "Weekend Warrior": (
                get_threshold_score(weekend_ratio, weekend_ratio_thresholds) * 2.5 +  # Boosted weight
                get_threshold_score(listening_frequency, listening_frequency_thresholds, reverse=True) * 1.5 +  # Boosted weight
                (1.5 if max_streak < 5 else 0) +  # Short listening streaks (boosted)
                (2.0 if weekend_ratio > 65 else 0) +  # Added: very high weekend ratio
                (1.5 if days_played < days_since_first * 0.4 else 0)  # Added: infrequent listener
            ),
            "Daily Listener": (
                get_threshold_score(listening_frequency, listening_frequency_thresholds) * 1.5 +  # Reduced weight
                get_threshold_score(weekend_ratio, weekend_ratio_thresholds, reverse=True) * 0.8 +  # Reduced weight
                get_threshold_score(max_streak, streak_thresholds) * 0.7 +  # Reduced weight
                (1.0 if total_plays / max(1, days_played) > 8 else 0)  # More specific condition
            ),
            "Skipper": (
                get_threshold_score(skip_rate, skip_rate_thresholds) * 2.0 +
                get_threshold_score(avg_play_minutes, avg_play_minutes_thresholds, reverse=True) * 1.5 +
                get_threshold_score(unique_ratio, unique_ratio_thresholds) * 0.8 +
                (1.0 if total_plays > 1000 else 0)  # High volume listener
            ),
            "Completionist": (
                get_threshold_score(skip_rate, skip_rate_thresholds, reverse=True) * 2.0 +  # Boosted weight
                get_threshold_score(avg_play_minutes, avg_play_minutes_thresholds) * 2.5 +  # Boosted weight
                (1.5 if album_to_artist_ratio > 1.2 else 0) +  # Complete albums (boosted)
                (1.5 if gini < 0.4 else 0) +  # Even listening across artists (boosted)
                (2.0 if skip_rate < 10 else 0) +  # Added: very low skip rate
                (1.5 if avg_play_minutes > 4.5 else 0)  # Added: very long average play time
            ),
            "Binge Listener": (
                (2.0 if max_streak > 10 else 0) +  # Long listening streaks (further reduced)
                get_threshold_score(total_plays, [500, 1000, 2000]) * 1.5 +  # Further reduced weight
                (1.4 if gini > 0.6 else 0) +  # Concentrated listening (further reduced)
                (1.2 if total_plays / max(1, days_played) > 10 else 0)  # Many plays per active day (further reduced)
            ),
            "Variety Seeker": (
                get_threshold_score(artists_count, artists_count_thresholds) * 1.5 +  # Reduced weight
                get_threshold_score(one_hits_pct, one_hits_thresholds) * 1.5 +  # Reduced weight
                (1.7 if artist_to_track_ratio > 0.5 else 0) +  # Many artists relative to tracks (slightly reduced)
                (1.5 if gini < 0.4 else 0)  # Even distribution across artists
            ),
            "Mood Listener": (
                get_threshold_score(skip_rate, skip_rate_thresholds) * 1.6 +  # Boosted weight
                (2.0 if weekend_ratio > 40 and weekend_ratio < 60 else 0) +  # Balanced weekend/weekday (boosted)
                get_threshold_score(unique_ratio, unique_ratio_thresholds) * 1.3 +  # Boosted weight
                (2.0 if listening_frequency > 0.3 and listening_frequency < 0.7 else 0)  # Moderate frequency (boosted)
            ),
            "Deep Diver": (
                get_threshold_score(avg_play_minutes, avg_play_minutes_thresholds) * 1.8 +  # Boosted weight
                (2.5 if album_to_artist_ratio > 2.0 else 0) +  # Multiple albums per artist (boosted)
                get_threshold_score(skip_rate, skip_rate_thresholds, reverse=True) * 1.4 +  # Boosted weight
                (2.0 if artists_count < 50 and tracks_count > 200 else 0) +  # Few artists but many tracks (boosted)
                (1.5 if gini > 0.5 and gini < 0.7 else 0)  # Added: moderate concentration on specific artists
            )
        }

        # Find the personality type with the highest score
        personality_type = max(scores.items(), key=lambda x: x[1])[0]

        # Define descriptions for each personality type
        descriptions = {
            "Explorer": "You're always seeking new music and artists. Your diverse taste spans many genres and you rarely get stuck in a musical rut.",
            "Loyalist": "You have deep connections with your favorite artists. When you find music you love, you stick with it and really get to know an artist's work.",
            "Eclectic": "Your playlist is a musical mosaic. You appreciate many different styles and aren't bound by genre conventions.",
            "Focused": "You know what you like and stick to it. Your listening is concentrated on specific genres or artists that resonate with you.",
            "Weekend Warrior": "Your music consumption spikes on weekends. Music is your companion for weekend activities and relaxation.",
            "Daily Listener": "Music is integrated into your daily routine. You have consistent listening habits throughout the week.",
            "Skipper": "You're quick to move on if a song doesn't grab you immediately. You're always searching for the perfect track for the moment.",
            "Completionist": "You appreciate music from start to finish. When you start a song or album, you tend to listen all the way through.",
            "Binge Listener": "You dive deep into music sessions, often listening for extended periods. When you find something you love, you immerse yourself completely.",
            "Variety Seeker": "You thrive on musical diversity. You're constantly exploring different artists and styles, rarely settling into predictable patterns.",
            "Mood Listener": "Your music choices are guided by your emotions. You select tracks that match or enhance your current mood, creating a personalized soundtrack for your life.",
            "Deep Diver": "You explore artists' catalogs thoroughly. Rather than sampling broadly, you prefer to discover everything about the artists you connect with."
        }

        # Calculate total score for percentage calculation
        total_score = sum(scores.values())

        # Calculate percentages for each personality type
        percentages = {}
        if total_score > 0:
            for ptype, score in scores.items():
                percentages[ptype] = (score / total_score) * 100
        else:
            # If total score is 0, distribute evenly
            even_percentage = 100 / len(scores)
            for ptype in scores.keys():
                percentages[ptype] = even_percentage

        return {
            "personality_type": personality_type,
            "personality_desc": descriptions.get(personality_type, "Your listening style is unique and defies easy categorization."),
            "personality_scores": scores,
            "personality_percentages": percentages
        }
    except Exception as e:
        logging.error(f"Error computing personality type: {e}")
        return {
            "personality_type": "Undefined",
            "personality_desc": "We couldn't determine your listening personality type."
        }

def calculate_all_stats(
    yearly: DefaultDict[int, Dict[str, DefaultDict[str, int]]],
    all_data: Dict[str, DefaultDict[str, int]],
    dates_set: Set[date],
    first_ts: datetime,
    first_entry: Dict[str, Any],
    last_ts: datetime,
    last_entry: Dict[str, Any],
    artist_set: Set[str],
    album_set: Set[str],
    track_set: Set[str],
    artist_tracks: DefaultDict[str, Set[str]],
    daily_counts: Counter,
    monthly_counts: Counter,
    weekday_counts: Counter,
    hour_counts: Counter,
    play_times: List[datetime],
    play_counted: int,
    skip_count: int,
    offline_count: int,
    track_skip_counts: Counter
) -> Dict[str, Any]:
    """
    Calculate all statistics for the Spotify streaming history.

    Args:
        yearly: Dictionary of yearly statistics
        all_data: Aggregated data for all years
        dates_set: Set of dates played
        first_ts: First timestamp
        first_entry: First entry
        last_ts: Last timestamp
        last_entry: Last entry
        artist_set: Set of artists
        album_set: Set of albums
        track_set: Set of tracks
        artist_tracks: Dictionary mapping artists to their tracks
        daily_counts: Counter of plays per day
        monthly_counts: Counter of plays per month
        weekday_counts: Counter of plays per weekday
        hour_counts: Counter of plays per hour
        play_times: List of play timestamps
        play_counted: Total number of plays counted
        skip_count: Number of skipped tracks
        offline_count: Number of offline plays
        track_skip_counts: Counter of skips per track

    Returns:
        Dict[str, Any]: Dictionary containing all statistics
    """
    # Calculate basic stats
    basic_stats = calculate_basic_stats(
        first_ts, first_entry, last_ts, last_entry, dates_set
    )

    # Calculate library stats
    library_stats = calculate_library_stats(
        artist_set, album_set, track_set, artist_tracks, yearly
    )

    # Calculate milestone stats
    milestone_stats = calculate_milestone_stats(
        daily_counts, all_data, yearly, monthly_counts
    )

    # Calculate pattern stats
    pattern_stats = calculate_pattern_stats(
        dates_set, daily_counts, weekday_counts, hour_counts
    )

    # Calculate session stats
    session_stats = calculate_session_stats(
        play_times, play_counted, skip_count, offline_count
    )

    # Calculate track stats
    track_stats = calculate_track_stats(
        all_data, track_set, track_skip_counts
    )

    # Combine all stats into a single dictionary
    all_stats = {}
    all_stats.update(basic_stats)
    all_stats.update(library_stats)
    all_stats.update(milestone_stats)
    all_stats.update(pattern_stats)
    all_stats.update(session_stats)
    all_stats.update(track_stats)

    # Calculate personality type
    personality_stats = calculate_personality_type(all_stats)
    all_stats.update(personality_stats)

    return all_stats
