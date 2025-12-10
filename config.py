import os
import logging

# Minimum number of milliseconds that you listened to the song.
#     Changing this will drastically alter the final counts.
MIN_MILLISECONDS = 20000


# Optional minimum year filter. If set (e.g., 2020), data before that year will be ignored.
# Set to None to disable year filtering.
MIN_YEAR = None


# Directory, or folder, on your computer where your Spotify JSON files are located.
#     The easiest method is to just put them in the sesh folder.
INPUT_DIR = "sesh/tmp"


# Name/path of the output file. If you don't change this, it will be in the same folder
#     as this script with the name summary.html. No need to add the .html
OUTPUT_FILE = "o"


def validate_config():
    """
    Validate configuration values and ensure they are within acceptable ranges.
    Creates directories if they don't exist and fixes invalid values.

    Returns:
        bool: True if validation succeeded, False if critical errors were found
    """
    global MIN_MILLISECONDS, INPUT_DIR, OUTPUT_FILE, MIN_YEAR

    # Validate MIN_MILLISECONDS
    if not isinstance(MIN_MILLISECONDS, int) or MIN_MILLISECONDS < 0:
        logging.warning(f"Invalid MIN_MILLISECONDS value: {MIN_MILLISECONDS}. Setting to default (20000).")
        MIN_MILLISECONDS = 20000

    # Validate MIN_YEAR (allow None to disable)
    if MIN_YEAR is not None:
        try:
            MIN_YEAR = int(MIN_YEAR)
            if MIN_YEAR < 1900 or MIN_YEAR > 3000:
                logging.warning(f"MIN_YEAR out of range: {MIN_YEAR}. Disabling year filter.")
                MIN_YEAR = None
        except (TypeError, ValueError):
            logging.warning(f"Invalid MIN_YEAR value: {MIN_YEAR}. Disabling year filter.")
            MIN_YEAR = None

    # Validate INPUT_DIR
    if not INPUT_DIR or not isinstance(INPUT_DIR, str):
        logging.error("INPUT_DIR cannot be empty and must be a string.")
        return False

    # Create the input directory if it doesn't exist
    try:
        if not os.path.exists(INPUT_DIR):
            logging.info(f"Creating input directory: {INPUT_DIR}")
            os.makedirs(INPUT_DIR, exist_ok=True)
    except Exception as e:
        logging.error(f"Failed to create input directory: {e}")
        return False

    # Validate OUTPUT_FILE
    if not OUTPUT_FILE or not isinstance(OUTPUT_FILE, str):
        logging.error("OUTPUT_FILE cannot be empty and must be a string.")
        return False

    # Check if the directory part of the output file path exists
    output_dir = os.path.dirname(OUTPUT_FILE)
    if output_dir:
        try:
            if not os.path.exists(output_dir):
                logging.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create output directory: {e}")
            return False

    return True
