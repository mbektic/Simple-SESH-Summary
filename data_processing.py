"""
Data processing module for Spotify Extended Streaming History.

This module contains functions for loading, validating, and processing
Spotify Extended Streaming History data.
"""
import json
import logging
import os
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any, Tuple, Set, DefaultDict, Optional, Generator

def validate_spotify_json(data: List[Dict[str, Any]]) -> bool:
    """
    Validate the structure of Spotify streaming history JSON data.

    Args:
        data (List[Dict[str, Any]]): The parsed JSON data to validate

    Returns:
        bool: True if the data is valid, False otherwise

    Raises:
        ValueError: If the data is not a list or is empty
    """
    if not isinstance(data, list):
        raise ValueError("Spotify data must be a list of entries")

    if not data:
        logging.warning("Spotify data is empty")
        return False

    # Check all entries for the basic structure
    required_fields = ['ts', 'ms_played']
    optional_metadata_fields = [
        'master_metadata_album_artist_name',
        'master_metadata_track_name',
        'master_metadata_album_album_name'
    ]

    valid_entries = 0
    invalid_entries = 0
    invalid_reasons = Counter()

    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            invalid_entries += 1
            invalid_reasons["not_dict"] += 1
            continue

        # Check that required fields exist
        missing_fields = [field for field in required_fields if field not in entry]
        if missing_fields:
            invalid_entries += 1
            invalid_reasons[f"missing_{','.join(missing_fields)}"] += 1
            continue

        # Validate timestamp format
        try:
            if not isinstance(entry["ts"], str):
                invalid_reasons["ts_not_string"] += 1
                continue

            # Try to parse the timestamp
            datetime.fromisoformat(entry["ts"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            invalid_entries += 1
            invalid_reasons["invalid_timestamp"] += 1
            continue

        # Validate ms_played is a positive number
        try:
            ms_played = entry["ms_played"]
            if not isinstance(ms_played, (int, float)) or ms_played < 0:
                invalid_entries += 1
                invalid_reasons["invalid_ms_played"] += 1
                continue
        except (KeyError, TypeError):
            invalid_entries += 1
            invalid_reasons["missing_ms_played"] += 1
            continue

        # Entry passed all validation checks
        valid_entries += 1

    # Log validation results
    total_entries = len(data)
    valid_percentage = (valid_entries / total_entries) * 100 if total_entries > 0 else 0

    if invalid_entries > 0:
        logging.warning(f"Found {invalid_entries} invalid entries out of {total_entries} ({invalid_entries/total_entries:.1%})")
        for reason, count in invalid_reasons.most_common():
            logging.warning(f"  - {reason}: {count} entries")

    # If at least 70% of the entries are valid, consider the data valid
    return valid_percentage >= 70.0

def load_spotify_json_files(input_dir: str) -> Generator[Dict[str, Any], None, None]:
    """
    Generator function to load and yield Spotify streaming history entries from JSON files.

    Args:
        input_dir (str): Directory containing JSON files

    Yields:
        Dict[str, Any]: Individual Spotify streaming history entries

    Raises:
        FileNotFoundError: If the input directory does not exist
    """
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Input directory '{input_dir}' does not exist")

    json_files = [
        os.path.join(input_dir, filename)
        for filename in os.listdir(input_dir)
        if filename.endswith(".json")
    ]

    if not json_files:
        logging.warning("⚠️ No JSON files found in the directory.")
        return

    total_files = len(json_files)
    logging.info(f"Loading data from {total_files} JSON files in {input_dir}")

    for i, file in enumerate(json_files, 1):
        try:
            logging.info(f"Processing file {i}/{total_files}: {os.path.basename(file)}")

            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate the JSON data structure
            if not validate_spotify_json(data):
                logging.warning(f"⚠️ File {file} has invalid data structure, skipping")
                continue

            # Yield entries one at a time
            for entry in data:
                yield entry

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"⚠️ Error reading {file}: {e}")
            continue
        except ValueError as e:
            logging.error(f"⚠️ Invalid data format in {file}: {e}")
            continue

def load_spotify_data(input_dir: str) -> List[Dict[str, Any]]:
    """
    Load Spotify streaming history data from JSON files in the specified directory.
    Performs validation, deduplication, and consistency checks on the data.
    Uses generators for memory-efficient processing of large datasets.

    Args:
        input_dir (str): Directory containing JSON files

    Returns:
        List[Dict[str, Any]]: List of valid Spotify streaming history entries

    Raises:
        FileNotFoundError: If the input directory does not exist
    """
    # Use generator to load entries
    all_entries = list(load_spotify_json_files(input_dir))

    if not all_entries:
        logging.warning("No valid entries found in any of the JSON files.")
        return []

    # Log the initial count of entries
    initial_count = len(all_entries)
    logging.info(f"Loaded {initial_count} entries")

    # Check for and remove duplicate entries
    logging.info("Checking for duplicate entries...")
    deduplicated_entries = check_for_duplicates(all_entries)

    # Perform data consistency checks
    logging.info("Performing data consistency checks...")
    validated_entries = perform_data_consistency_checks(deduplicated_entries)

    # Log the final count of entries
    final_count = len(validated_entries)
    if final_count != initial_count:
        logging.info(f"After validation and deduplication: {final_count} entries ({initial_count - final_count} removed)")

    return validated_entries

def process_entry(
    entry: Dict[str, Any], 
    min_milliseconds: int,
    yearly: DefaultDict[int, Dict[str, DefaultDict[str, int]]],
    dates_set: Set[datetime.date],
    first_ts: Optional[datetime],
    first_entry: Optional[Dict[str, Any]],
    last_ts: Optional[datetime],
    last_entry: Optional[Dict[str, Any]],
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
) -> Tuple[
    DefaultDict[int, Dict[str, DefaultDict[str, int]]],
    Set[datetime.date],
    Optional[datetime],
    Optional[Dict[str, Any]],
    Optional[datetime],
    Optional[Dict[str, Any]],
    Set[str],
    Set[str],
    Set[str],
    DefaultDict[str, Set[str]],
    Counter,
    Counter,
    Counter,
    Counter,
    List[datetime],
    int,
    int,
    int,
    Counter
]:
    """
    Process a single Spotify streaming history entry and update statistics.

    Args:
        entry (Dict[str, Any]): The entry to process
        min_milliseconds (int): Minimum milliseconds for a play to count
        yearly: Dictionary of yearly statistics
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
        Tuple containing updated statistics
    """
    try:
        # Skip entries with no playtime or missing required fields
        if not entry.get("ms_played") or entry["ms_played"] <= 0:
            return (
                yearly, dates_set, first_ts, first_entry, last_ts, last_entry,
                artist_set, album_set, track_set, artist_tracks, daily_counts,
                monthly_counts, weekday_counts, hour_counts, play_times,
                play_counted, skip_count, offline_count, track_skip_counts
            )

        # Skip entries with a missing timestamp
        if "ts" not in entry:
            logging.warning(f"Entry missing timestamp, skipping: {entry.get('master_metadata_track_name', 'Unknown track')}")
            return (
                yearly, dates_set, first_ts, first_entry, last_ts, last_entry,
                artist_set, album_set, track_set, artist_tracks, daily_counts,
                monthly_counts, weekday_counts, hour_counts, play_times,
                play_counted, skip_count, offline_count, track_skip_counts
            )

        # Year Filter
        # if int(entry.get("ts")[:4]) < 2018:
        #     logging.info(f"Skipping entry because it's less than the year filter, skipping: {entry.get('master_metadata_track_name', 'Unknown track')} Time: {entry.get('ts')[:4]}")
        #     return (
        #         yearly, dates_set, first_ts, first_entry, last_ts, last_entry,
        #         artist_set, album_set, track_set, artist_tracks, daily_counts,
        #         monthly_counts, weekday_counts, hour_counts, play_times,
        #         play_counted, skip_count, offline_count, track_skip_counts
        #         )

        # Process entries with artist information
        if entry.get("master_metadata_album_artist_name"):
            # Get the artist name or use fallback
            artist = entry.get("master_metadata_album_artist_name", "Unknown Artist")

            # Handle missing track or album names gracefully
            track_name = entry.get("master_metadata_track_name", "Unknown Track")
            album_name = entry.get("master_metadata_album_album_name", "Unknown Album")

            # Create full track and album identifiers
            track = f"{track_name} - {artist}"
            album = f"{album_name} - {artist}"

            # Parse timestamp with error handling
            try:
                dt = datetime.fromisoformat(entry["ts"].replace("Z", "+00:00"))
                year = dt.year
            except (ValueError, TypeError) as e:
                logging.warning(f"Invalid timestamp format in entry, using current year: {e}")
                dt = datetime.now()
                year = dt.year

            y = yearly[year]

            # ─── update stats info ─────────────────────────────────
            dates_set.add(dt.date())
            if first_ts is None or dt < first_ts:
                first_ts = dt
                first_entry = entry
            if last_ts is None or dt > last_ts:
                last_ts = dt
                last_entry = entry

            if entry["ms_played"] > min_milliseconds:
                daily_counts[dt.date()] += 1
                monthly_counts[(dt.year, dt.month)] += 1
                weekday_counts[dt.weekday()] += 1
                hour_counts[dt.hour] += 1
                play_times.append(dt)
                play_counted += 1
                if entry.get("offline"):
                    offline_count += 1

            if entry.get("skipped"):
                skip_count += 1
                track_skip_counts[track] += 1

            artist_set.add(artist)
            track_set.add(track)
            album_set.add(album)
            artist_tracks[artist].add(track)
            # ───────────────────────────────────────────────────────────

            # Update counts and times
            if entry.get("ms_played") > min_milliseconds:
                y["artist_counts"][artist] += 1
                y["track_counts"][track] += 1
                y["album_counts"][album] += 1

            # Update play times
            y["artist_time"][artist] += entry["ms_played"]
            y["track_time"][track] += entry["ms_played"]
            y["album_time"][album] += entry["ms_played"]
    except Exception as e:
        # Catch any unexpected errors during entry processing
        logging.error(f"Error processing entry: {e}")

    return (
        yearly, dates_set, first_ts, first_entry, last_ts, last_entry,
        artist_set, album_set, track_set, artist_tracks, daily_counts,
        monthly_counts, weekday_counts, hour_counts, play_times,
        play_counted, skip_count, offline_count, track_skip_counts
    )

def process_spotify_data(entries: List[Dict[str, Any]], min_milliseconds: int, min_year: Optional[int] = None) -> tuple[
    defaultdict[Any, dict[str, defaultdict[Any, int]]] | defaultdict[int, dict[str, defaultdict[str, int]]], set[
        Any], datetime | None, dict[str, Any] | None, datetime | None, dict[str, Any] | None, set[Any] | set[str], set[
        Any] | set[str], set[Any] | set[str], defaultdict[Any, set] | defaultdict[str, set[str]], Counter[
        Any] | Counter, Counter[Any] | Counter, Counter[Any] | Counter, Counter[Any] | Counter, list[Any] | list[
        datetime], int, int, int, Counter[Any] | Counter, str]:
    """
    Process Spotify streaming history entries and extract statistics.
    Uses a generator-based approach for memory efficiency.

    Args:
        entries (List[Dict[str, Any]]): List of Spotify streaming history entries
        min_milliseconds (int): Minimum milliseconds for a play to count
        min_year (Optional[int]): If provided, ignore entries with year < min_year

    Returns:
        Tuple containing various statistics:
            - yearly: Dictionary of yearly statistics
            - dates_set: Set of dates played
            - first_ts: First timestamp
            - first_entry: First entry
            - last_ts: Last timestamp
            - last_entry: Last entry
            - artist_set: Set of artists
            - album_set: Set of albums
            - track_set: Set of tracks
            - artist_tracks: Dictionary mapping artists to their tracks
            - daily_counts: Counter of plays per day
            - monthly_counts: Counter of plays per month
            - weekday_counts: Counter of plays per weekday
            - hour_counts: Counter of plays per hour
            - play_times: List of play timestamps
            - play_counted: Total number of plays counted
            - skip_count: Number of skipped tracks
            - offline_count: Number of offline plays
            - track_skip_counts: Counter of skips per track
    """
    yearly = defaultdict(lambda: {
        "artist_counts": defaultdict(int),
        "artist_time": defaultdict(int),
        "track_counts": defaultdict(int),
        "track_time": defaultdict(int),
        "album_counts": defaultdict(int),
        "album_time": defaultdict(int),
    })

    dates_set = set()
    first_ts = None
    first_entry = None
    last_ts = None
    last_entry = None
    artist_set = set()
    album_set = set()
    track_set = set()
    artist_tracks = defaultdict(set)
    daily_counts = Counter()
    monthly_counts = Counter()
    weekday_counts = Counter()
    hour_counts = Counter()
    play_times = []
    play_counted = 0
    skip_count = 0
    offline_count = 0
    track_skip_counts = Counter()

    # Process entries one at a time
    for entry in entries:
        # Year filter (skip entries before min_year)
        if min_year is not None:
            try:
                ts = datetime.fromisoformat(entry["ts"].replace("Z", "+00:00"))
                if ts.year < min_year:
                    continue
            except Exception:
                # If timestamp is bad, let process_entry handle validation/logging
                pass
        (
            yearly, dates_set, first_ts, first_entry, last_ts, last_entry,
            artist_set, album_set, track_set, artist_tracks, daily_counts,
            monthly_counts, weekday_counts, hour_counts, play_times,
            play_counted, skip_count, offline_count, track_skip_counts
        ) = process_entry(
            entry, min_milliseconds, yearly, dates_set, first_ts, first_entry, 
            last_ts, last_entry, artist_set, album_set, track_set, artist_tracks, 
            daily_counts, monthly_counts, weekday_counts, hour_counts, play_times,
            play_counted, skip_count, offline_count, track_skip_counts
        )

    date_to_tracks = defaultdict(Counter)
    for entry in entries:
        if entry.get("ms_played", 0) > min_milliseconds:
            dt_full = datetime.fromisoformat(entry["ts"].replace("Z", "+00:00"))
            if min_year is not None and dt_full.year < min_year:
                continue
            dt = dt_full.date()
            mmdd = dt.strftime("%m-%d")
            full_date = dt.isoformat()
            track_name = entry.get("master_metadata_track_name", "Unknown Track")
            artist = entry.get("master_metadata_album_artist_name", "Unknown Artist")
            track = f"{track_name} — {artist}"
            date_to_tracks[mmdd][(track, full_date)] += 1

    # Convert to JSON-ready format, excluding any entries with only 1 play
    otd = {}
    for mmdd, ctr in date_to_tracks.items():
        otd[mmdd] = [
            {"track": track, "date": date, "count": count}
            for (track, date), count in ctr.items()
            if count > 2
        ]

    otd_json = json.dumps(otd, indent=2)

    return (
        yearly, dates_set, first_ts, first_entry, last_ts, last_entry,
        artist_set, album_set, track_set, artist_tracks, daily_counts,
        monthly_counts, weekday_counts, hour_counts, play_times,
        play_counted, skip_count, offline_count, track_skip_counts, otd_json
    )

def process_entry_for_deduplication(entry: Dict[str, Any], unique_entries: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], bool]:
    """
    Process a single entry for deduplication.

    Args:
        entry (Dict[str, Any]): The entry to process
        unique_entries (Dict[str, Dict[str, Any]]): Dictionary of unique entries seen so far

    Returns:
        Tuple[Dict[str, Dict[str, Any]], bool]: Updated unique_entries dictionary and a boolean indicating if the entry was a duplicate
    """
    try:
        ts = entry.get("ts", "")
        track = entry.get("master_metadata_track_name", "Unknown Track")
        artist = entry.get("master_metadata_album_artist_name", "Unknown Artist")
        ms_played = entry.get("ms_played", 0)

        # Create a unique identifier for this entry
        entry_key = f"{ts}|{track}|{artist}|{ms_played}"

        is_duplicate = entry_key in unique_entries
        if not is_duplicate:
            unique_entries[entry_key] = entry

        return unique_entries, is_duplicate
    except Exception as e:
        logging.error(f"Error processing entry for duplicate check: {e}")
        # Return the entry as non-duplicate in case of error to avoid data loss
        return unique_entries, False

def check_for_duplicates(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Check for and remove duplicate entries in the Spotify streaming history data.
    Uses a generator-based approach for memory efficiency.

    Args:
        entries (List[Dict[str, Any]]): List of Spotify streaming history entries

    Returns:
        List[Dict[str, Any]]: List of entries with duplicates removed
    """
    if not entries:
        return []

    # Create a dictionary to track unique entries
    unique_entries = {}
    duplicates = 0

    # Process entries one at a time
    for entry in entries:
        unique_entries, is_duplicate = process_entry_for_deduplication(entry, unique_entries)
        if is_duplicate:
            duplicates += 1

    if duplicates > 0:
        logging.info(f"Removed {duplicates} duplicate entries from dataset")

    return list(unique_entries.values())

def fix_entry_consistency(entry: Dict[str, Any], inconsistencies: Counter) -> Dict[str, Any]:
    """
    Fix consistency issues in a single Spotify streaming history entry.

    Args:
        entry (Dict[str, Any]): The entry to check and fix
        inconsistencies (Counter): Counter to track types of inconsistencies

    Returns:
        Dict[str, Any]: The fixed entry
    """
    try:
        # Create a copy of the entry to avoid modifying the original
        fixed_entry = entry.copy()

        # Check for unreasonably large ms_played values (more than 24 hours)
        if fixed_entry.get("ms_played", 0) > 24 * 60 * 60 * 1000:
            fixed_entry["ms_played"] = 24 * 60 * 60 * 1000  # Cap at 24 hours
            inconsistencies["excessive_playtime"] += 1

        # Check for future timestamps
        if "ts" in fixed_entry:
            try:
                ts = datetime.fromisoformat(fixed_entry["ts"].replace("Z", "+00:00"))
                now = datetime.now()
                if ts > now:
                    # Set to the current time if in the future
                    fixed_entry["ts"] = now.isoformat()
                    inconsistencies["future_timestamp"] += 1
            except (ValueError, TypeError):
                # Already logged in validation function
                pass

        # Check for missing artist but present track or album
        if (not fixed_entry.get("master_metadata_album_artist_name") and 
            (fixed_entry.get("master_metadata_track_name") or fixed_entry.get("master_metadata_album_album_name"))):
            fixed_entry["master_metadata_album_artist_name"] = "Unknown Artist"
            inconsistencies["missing_artist"] += 1

        # Check for missing track but present artist
        if (not fixed_entry.get("master_metadata_track_name") and 
            fixed_entry.get("master_metadata_album_artist_name")):
            fixed_entry["master_metadata_track_name"] = "Unknown Track"
            inconsistencies["missing_track"] += 1

        # Check for a missing album but present artist
        if (not fixed_entry.get("master_metadata_album_album_name") and 
            fixed_entry.get("master_metadata_album_artist_name")):
            fixed_entry["master_metadata_album_album_name"] = "Unknown Album"
            inconsistencies["missing_album"] += 1

        return fixed_entry
    except Exception as e:
        logging.error(f"Error during consistency check: {e}")
        # Return the original entry to avoid data loss
        return entry

def perform_data_consistency_checks(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Perform data consistency checks on Spotify streaming history entries.
    Uses a generator-based approach for memory efficiency.

    Args:
        entries (List[Dict[str, Any]]): List of Spotify streaming history entries

    Returns:
        List[Dict[str, Any]]: List of entries with inconsistencies fixed where possible
    """
    if not entries:
        return []

    fixed_entries = []
    inconsistencies = Counter()

    # Process entries one at a time
    for entry in entries:
        fixed_entry = fix_entry_consistency(entry, inconsistencies)
        fixed_entries.append(fixed_entry)

    # Log inconsistency statistics
    if sum(inconsistencies.values()) > 0:
        logging.info(f"Fixed {sum(inconsistencies.values())} data inconsistencies:")
        for reason, count in inconsistencies.most_common():
            logging.info(f"  - {reason}: {count}")

    return fixed_entries

def aggregate_yearly_data(yearly: DefaultDict[int, Dict[str, DefaultDict[str, int]]]) -> Dict[str, DefaultDict[str, int]]:
    """
    Aggregate yearly data into a single "all years" dataset.

    Args:
        yearly (DefaultDict[int, Dict[str, DefaultDict[str, int]]]): Dictionary of yearly statistics

    Returns:
        Dict[str, DefaultDict[str, int]]: Aggregated statistics for all years
    """
    all_data = {
        "artist_counts": defaultdict(int),
        "artist_time": defaultdict(int),
        "track_counts": defaultdict(int),
        "track_time": defaultdict(int),
        "album_counts": defaultdict(int),
        "album_time": defaultdict(int),
    }

    for ydata in yearly.values():
        for key in ["artist_counts", "track_counts", "album_counts"]:
            for name, cnt in ydata[key].items():
                all_data[key][name] += cnt
        for key in ["artist_time", "track_time", "album_time"]:
            for name, t in ydata[key].items():
                all_data[key][name] += t

    return all_data
