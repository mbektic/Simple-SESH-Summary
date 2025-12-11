"""
Generate HTML summary from Spotify Extended Streaming History.

This script generates an HTML summary report from Spotify Extended Streaming History
JSON files. It uses the data_processing, statistics, and html_generation modules
to process the data, calculate statistics, and generate the HTML report.
"""
import argparse
import sys
from typing import Any

from gui import *
from data_processing import load_spotify_data, process_spotify_data, aggregate_yearly_data
from html_generation import build_year_tabs, build_year_dropdown, build_all_section, build_year_sections, build_stats_html, \
    generate_html_content, write_html_to_file, generate_personality_html, build_tables_data
from statistics import calculate_all_stats
from logging_config import configure_logging, log_exception, log_system_info

# The script version. You can check the changelog at the GitHub URL to see if there is a new version.
VERSION = "1.18.0"
GITHUB_URL = "https://github.com/mbektic/Simple-SESH-Sumary/blob/main/CHANGELOG.md"

# Parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description='Generate HTML summary from Spotify Extended Streaming History')
    parser.add_argument('--log-level', choices=['debug', 'info', 'warning', 'error', 'critical'],
                        default='info', help='Set the logging level (default: info)')
    parser.add_argument('--log-file', help='Specify a log file name')
    parser.add_argument('--no-console-log', action='store_true', help='Disable console logging')
    parser.add_argument('--skip-gui', action='store_true', help='Skip GUI and use config.py values')
    return parser.parse_args()

# Configure logging based on command line arguments
args = parse_args()
configure_logging(
    level=args.log_level,
    log_file=args.log_file,
    console=not args.no_console_log
)

# Log system information for troubleshooting
log_system_info()

def count_plays_from_directory(config: Any, progress_callback=None) -> None:
    """
    Process Spotify streaming history JSON files and generate an HTML summary report.

    Args:
        config: Configuration object with attributes:
            - MIN_MILLISECONDS: Minimum milliseconds for a play to count
            - INPUT_DIR: Directory containing JSON files
            - OUTPUT_FILE: Base name for the output HTML file
        progress_callback: Optional callback function to report progress.
            The callback should accept two parameters:
            - step (str): The current processing step
            - progress (float): Progress value between 0.0 and 1.0

    Returns:
        None

    Raises:
        FileNotFoundError: If the input directory does not exist.
        PermissionError: If files cannot be read or written due to permission issues
    """
    MIN_MILLISECONDS = config.MIN_MILLISECONDS
    input_dir = config.INPUT_DIR
    output_html = config.OUTPUT_FILE + ".html"

    # Define a helper function to update progress
    def update_progress(step, progress):
        if progress_callback:
            progress_callback(step, progress)
        logging.info(f"Progress: {step} - {progress:.1%}")

    # Start processing
    update_progress("Starting", 0.0)

    try:
        # Load Spotify data from JSON files
        update_progress("Loading data", 0.1)
        try:
            entries = load_spotify_data(input_dir)
            if not entries:
                logging.warning("No valid entries found in the input directory.")
                update_progress("Completed", 1.0)
                return
        except Exception as e:
            logging.error(f"Error loading Spotify data: {e}")
            log_exception()
            raise

        # Process Spotify data
        update_progress("Processing data", 0.3)
        try:
            (
                yearly, dates_set, first_ts, first_entry, last_ts, last_entry,
                artist_set, album_set, track_set, artist_tracks, daily_counts,
                monthly_counts, weekday_counts, hour_counts, play_times,
                play_counted, skip_count, offline_count, track_skip_counts, otd_data, daily_entity
            ) = process_spotify_data(entries, MIN_MILLISECONDS, getattr(config, 'MIN_YEAR', None))
        except Exception as e:
            logging.error(f"Error processing Spotify data: {e}")
            log_exception()
            raise

        # Aggregate yearly data
        update_progress("Aggregating data", 0.5)
        try:
            all_data = aggregate_yearly_data(yearly)
        except Exception as e:
            logging.error(f"Error aggregating yearly data: {e}")
            log_exception()
            raise

        # Calculate all statistics
        update_progress("Calculating statistics", 0.6)
        try:
            stats_data = calculate_all_stats(
                yearly, all_data, dates_set, first_ts, first_entry, last_ts, last_entry,
                artist_set, album_set, track_set, artist_tracks, daily_counts,
                monthly_counts, weekday_counts, hour_counts, play_times,
                play_counted, skip_count, offline_count, track_skip_counts
            )
        except Exception as e:
            logging.error(f"Error calculating statistics: {e}")
            log_exception()
            raise

        # Build HTML content
        update_progress("Building HTML", 0.7)
        try:
            years = sorted(yearly.keys())
            tabs = build_year_tabs(years)
            year_dropdown = build_year_dropdown(years)
            all_section = build_all_section(all_data)
            year_sections = build_year_sections(years)
            sections = all_section + year_sections
            stats_html = build_stats_html(stats_data, daily_counts, otd_data, yearly)
            table_data = build_tables_data(all_data, yearly, daily_entity)
        except Exception as e:
            logging.error(f"Error building HTML content: {e}")
            log_exception()
            raise

        # Generate personality HTML
        personality_html = generate_personality_html(stats_data)

        # Generate complete HTML content
        update_progress("Generating HTML", 0.8)
        try:
            html_content = generate_html_content(
                tabs, sections, stats_html, GITHUB_URL, VERSION, personality_html, year_dropdown, table_data
            )
        except Exception as e:
            logging.error(f"Error generating HTML content: {e}")
            log_exception()
            raise

        # Write HTML content to a file
        update_progress("Writing HTML file", 0.9)
        try:
            write_html_to_file(html_content, output_html)
        except Exception as e:
            logging.error(f"Error writing HTML file: {e}")
            log_exception()
            raise

        # Complete
        update_progress("Completed", 1.0)

    except Exception as e:
        logging.error(f"Unexpected error in count_plays_from_directory: {e}")
        log_exception()
        raise


if __name__ == "__main__":
    try:
        if args.skip_gui or (len(sys.argv) > 1 and sys.argv[1].lower() == 'true'):
            logging.info("Running in command-line mode")
            config = load_config()
            # Validate configuration before processing
            if not config.validate_config():
                logging.error("Configuration validation failed. Please check your config.py file.")
                sys.exit(1)
            try:
                count_plays_from_directory(config)
            except Exception as e:
                logging.error(f"Error during processing: {e}")
                log_exception()
                sys.exit(1)
        else:
            logging.info("Starting GUI")
            root = tk.Tk()
            app = ConfigApp(root)
            load_style(root)
            root.mainloop()
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}")
        log_exception()
        sys.exit(1)
