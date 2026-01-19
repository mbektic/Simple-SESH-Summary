# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.20.0] 2026-01-18
### Added 
- Added new stats when you click on playtime. 
  - Total Per Year 
  - Over the years 
  - Change over Years

## [1.19.3] 2026-01-02
### Added 
- Added missing HTML files not included due to the gitignore. 

## [1.19.2] 2025-12-14
### Added 
- 11 New Smart Playlists
  - Including the "Seasonal Echoes" playlist, Which is dynamically generated unlike the other playlists. 
  
### Changed 
- Smart Playlist are now sorted alphabetically.

### Fixed
- Fixed Unknown Artist/Track/Album showing up.

## [1.19.1] 2025-12-14
### Fixed
- Items-per-page setting now persists consistently across All, specific years, and Custom range when navigating between them and when toggling Playtime/Playcount.

## [1.19.0] 2025-12-14
### Added 
- Added a new "Smart Playlist"
- Made "On This Day" songs clickable, opening Spotify.
- Made "Tracks" table songs clickable, opening Spotify.

### Fixed
- Search is now working again.
- Fixed styling on for "On This Day"
- Fixed "On this Day" starting at 1. on every page.
- Fixed scrolling braking after changing table size in setting. 
- Prevent background page from scrolling when modals are open, avoiding unintended page interactions.

## [1.18.2] 2025-12-11
### Changed
- Using the data added in `1.18.0` changed On This Day to generate on the fly instead of being built in the HTML file.
    - This brought the file size down from ~5.4MB to ~4.9MB.
- Increased the compression level and switched to using deterministic JSON serialization.
  - Didn't decrease size much, but it's still better than the previous version.
- Replaced object‑heavy JSON with columnar/array schema.

## [1.18.1] 2025-12-11
### Fixed
- Fixed a bug with iPhones where there were two "Custom..." options showing up.

## [1.18.0] 2025-12-11
### Added 
- Added the ability to set a custom date range for the tables. 
  - Though the last update brought us down to 2.4MB, all the new data brings us back to ~5.3MB but it will allow for new features in the future, like this one.

## [1.17.0] 2025-12-10
### Added 
- Wrote crude minify functions for the resulting HTML file.
- Added the ability to compress the JSON in the resulting HTML file, with a config option to turn it off.

### Changed
- Altered how the table data is stored in the resulting HTML file, resulting in a much smaller file size.
  - My 11-year summary was 18.9MB
  - With JSON compression it's 2.4MB
  - Without JSON compression it's 4.5MB
- Cleand up how tables are generated.
- More improvements to the mobile styling.

## [1.16.2] 2025-12-10
### Changed
- The year selector is now a dropdown instead of a tab menu on mobile.
- A lot more appearance improvements.

### Fixed
- Removed the emojis for real this time. 
- Fixed placeholder text for search bars. Was broken when I removed the Emojis.
- Fixed default config.json settings. 

## [1.16.1] 2025-12-10
### Changed
- Removed the emojis since they were kinda cringy.

## [1.16.0] 2025-12-10
### Added 
- New "Listening by Year" mini chart in the Stats section showing your listening per year.
- Added a new Minimum Year filter.

### Changed
- Changed the default format for timestamps from HH:MM:SS to 09h 27m 51s
- Fixed some minor styling issues.

### Fixed
- Mobile styling for "On This Day" section

## [1.15.3] 2025-05-07
### Changed 
- Switched the info buttons tooltips to show on click instead of hover. 

## [1.15.2] 2025-05-07
### Changed
- Set the default font to `JetBrains Mono - monospace` as it comes off more legible, will still fall back to `Courier New - monospace` if the font is not available.
- Updated On This Day output section.

### Fixed
- Removed random floating `'` above the version number. 

## [1.15.1] 2025-05-07
### Changed
- Changed the bar scaling inside the Personality Type graph to scale off the highest value instead of 100%. 

## [1.15.0] 2025-05-07
### Added
- New Listening Personality Type with several different personalities and calculations.
  - Weights were set based off of only four different sets of data and may need to be adjusted.

### Changed
- Changed info-buttons to use tippy.js tooltips instead of modal dialogs.
- Removed unused info-modal code from JavaScript and HTML generation.
- Updated the default width of tippy.js tooltips to be 50em.

## [1.14.2] 2025-05-06
### Added
- Added tippy.js and popper.js to the project.

### Changed
- Greatly improved the hover effect on the Activity Heatmap.

## [1.14.1] 2025-05-03
### Changed
- Cleaned up some JS and CSS to make the final output slightly smaller.

## [1.14.0] 2025-05-03
### Added
- Added a new "On This Day" section to the stats to see what songs you had on repeat in past years on the same date.

### Changed
- Cleared the default directory in `config.py` since the `sesh` folder is gone.

## [1.13.4] 2025-05-03
### Changed
- Updated GUI text to be more helpful.

## [1.13.3] 2025-05-03
### Changed
- The input directory in the gui is now a file input instead of a text input.

### Removed
- Removed the `readme.md` file in the sesh folder.

## [1.13.2] 2025-05-02
### Added
- There is now an "Items per page option" in the settings.
- Added an on hover effect to the Activity Heatmap

### Changed
- Artist every year limits itself to the same `MIN_MILLISECONDS` value.
- Made the Activity Heatmap squares larger on mobile. 

### Removed
- `ITEMS_PER_PAGE` config option was removed from the config and the GUI.

## [1.13.1] 2025-04-30
### Fixed
- Fixed missing information text for the "number of sessions" stat

### Removed
- Removed some useless logging. 

## [1.13.0] 2025-04-30
### Added
- Added a "GitHub" style Activity Heatmap
- Added def validate_config() function in `config.py` that I forgot to include last time. 

## [1.12.0] 2025-04-30
### Added
- Added validation for configuration values 
- Added data integrity checks 
- Progress indicator was added to the GUI 
- Added a comprehensive logging system with:
  - Detailed error logs with file, line number, and function information
  - Log file output with automatic rotation
  - Command-line options for controlling log verbosity
  - Exception logging with full traceback information

### Changed
- Improved memory efficiency by using generators for large data transformations:
  - Modified data loading to process files one at a time
  - Implemented entry-by-entry processing for better memory usage
  - Reduced memory footprint for large datasets

## [1.11.2] 2025-04-30
### Changed
- Renamed `Gui.py` to `gui.pi` to better fit the rest of the filenames.
- Renamed `Config.py` to `config.pi` to better fit the rest of the filenames.
- Cleaned up some comments

## [1.11.1] 2025-04-30
### Fixed
- Fixed input validation on minimum milliseconds

## [1.11.0] 2025-04-30
### Changed
- Refactored GenerateHTMLSummary.py into smaller, more focused modules:
  - Created `data_processing.py` for data loading and processing functions
  - Created `statistics.py` for statistics calculation functions
  - Created `html_generation.py` for HTML generation functions
- Improved code organization and maintainability

## [1.10.0] 2025-04-30
### Added
- Added JSON data structure validation
- Added type hints for better IDE support
- Added proper exception handling for file operations
- Added docstrings to functions
- Added input validation for GUI fields
- Added graceful degradation for missing or corrupt data
- Added comprehensive error handling throughout the application
- Added total plays stat
- Added input validation for GUI fields
- Added graceful degradation for missing or corrupt data
- Added comprehensive error handling throughout the application
- Added keyboard navigation support for all interactive elements
- Added ARIA attributes for improved screen reader support
- Added focus management for modals and dialogs
- Added enhanced user-friendly error messages in the GUI,

### Changed
- Replaced print statements with logging calls

### Fixed
- Fixed highlighting not working after searching and changing the page.

## [1.9.1] 2025-04-30
### Changed
- Regrouped the stats to make them easier to digest.

### Fixed
- You can no longer scroll around while everything is loading, this should also hopefully fix the jumping of the loading screen.
- Fixed where tapping outside the info modal on mobile would not close it. 

## [1.9.0] 2025-04-29
### Added
- Unique Tracks Ratio stat
- Gini Coefficient of Artist Plays stat
- Weekend vs. Weekday Ratio stat
- Number of listening sessions stat
- Average session length stat
- Longest single session stat
- Skip rate stat
- Offline vs. Online ratio stat
- Total listening time stat
- Average playtime per play stat
- Most skipped track stat
- Longest hiatus stat
- Most popular week/day stats

### Changed 
- Changed the info button on stats to match the theme.

## [1.8.0] 2025-04-29
### Added 
- Eddington number stats
- Artist cut-over point stat
- Most popular year/month stats
- Longest Listening Streak stat
- Average Plays per Active Day stat
- Most Active Weekday stat
- Peak Listening Hour stat

### Changed
- Cleaned up stats grouping to make it more human-friendly.

### Fixed
- Fixed jumping of the loading screen on mobile (for real this time)

## [1.7.1] 2025-04-29
### Changed
- General formating changes.  

### Fixed
- Fixed jumping of the loading screen on mobile.

## [1.7.0] 2025-04-29
### Added
- Added a new stats section to the bottom of the page with some general fun stats. 

## [1.6.2] 2025-04-29
### Changed
- Check to ensure the total time played is more than 0 ms to get rid of useless data.

## [1.6.1] 2025-04-29
### Changed
- Search now persists when switching between tabs. 

### Fixed
- Fixed mode toggle not working anymore after the tab update.

## [1.6.0] 2025-04-29
### Added
- Year selector for the tables so you can see the data based off of the year. 

## [1.5.1] 2025-04-22
### Added
- Text highlighting on search terms. 

### Changed
- The page title is now "Spotify Summary"
- Moved the title bar and loading page to a new HTML file
- If there are no search results, a "No results found" message will be shown.
- Milliseconds always now format with three digits for consistency

## [1.5.0] 2025-04-22
### Added
- New header bar with a settings menu and moved the dark theme slide and the play mode switch under it. 

### Changed
- Moved the `PLAYTIME_MODE` setting into the app instead of a config option so one resulting page can view both.
- Switched to spotify green instead of red.
- Moved some of the HTML to its own file `html/settings_moda.html` to make the project easier to manage. I want to move more in the future. 
- Update `print_file()` function to be able to handle emojis 

### Removed
- `PLAYTIME_MODE` setting was removed from the config and the GUI
- The fancy dark mode slider had to go, it was nice looking but a pain in the behind. 

## [1.4.0] 2025-04-21
### Added
- New GUI for the app that makes it easy to edit parameters without editing the config file.

### Changed
- `OUTPUT_FILE` no longer needs .html, and all created files will always be HTML.

### Fixed
- `MIN_MILLISECONDS` wasn't being used so this was fixed.

## [1.3.2] 2025-04-21
### Changed
- Increased the fade out time to one second, so on small datasets it doesn't just look like the screen is flashing
- The size of the loading text and spinner was updated.
- No longer remove the loading screen from the layout in case I need it again. 

## [1.3.1] 2025-04-21
### Added
- Loading screen while the tables are paginating.
- Added missing `<!DOCTYPE html>` to get rid of annoying warning

### Changed
- Move `window.onload` function to `scripts.js`
- Text changes for search boxes and the second table column.

### Fixed
- Fixed weird behaviors setting the default theme and loading the selected theme

## [1.3.0] 2025-04-21
### Added
- Search functionality.
- Added a dark_mode toggle button. 

### Changed
- Rewrote the pagination functions to drastically improve render time. 8–10 seconds with my full data to about 3 in firefox, 1 second in Chromium-based browsers. 
- Redid the light theme to make it better along with some other minor styling changes.
- Imported * from config to clean up code.
- Changed Page Title to "Spotify Streaming History"

### Removed
- Removed `DARK_MODE` config option

## [1.2.3] 2025-04-21
### Added 
- Mobile Styling

### Changed
- Updated playtime column header so it looks better on mobile.
- Moved config variables to their own file for user easy of use. 
- Other minor styling updates. 
- Reduced the page window from 2 to 1 so the page selector fits better. 

## [1.2.2] 2025-04-20
### Changed
- Text updates.

## [1.2.1] 2025-04-20
### Changed
- JavaScript was moved to its own file to make it easier to edit.
- Added milliseconds to playtime mode.

### Fixed
- Fixed table columns jumping around when switching pages. 

## [1.2.0] 2025-04-19
### Added
- New dark mode option

### Changed 
- Styles are now in CSS files to make them easier to manage, with three files `stlye.css`, `light.css` and `dark.css`
- General styling changes for readability.
- Updated `README.md`

## [1.1.3] 2025-04-19
### Changed 
- Playtime chart tables names now say `Play Time` instead of `Play Count`.
- Changed the font to `Courier New - monospace` as it comes off more legible.
- Updated screenshots in readme.

## [1.1.2] 2025-04-19
### Added 
- Added a .gitignore

## [1.1.1] 2025-04-19
### Fixed
- Fixed spelling of `CHANGELOG.md` to be correct.

## [1.1.0] 2025-04-19
### Added
- Added a new `PLAYTIME_MODE` flag that will make the script generate the ranking based off of milliseconds listened instead of raw playcount.
- Added `CHANGELOG.md`
- Added version number to the bottom of the HTML page so users can quickly see what version they are using and if there's a new one available

### Changed
- Minor Style changes.

## [1.0.0] - 2025-04-17
### Added
- Initial Release
## [1.19.4] 2025-12-14
### Changed
- Moved all inline Seasonal Echoes and Smart Playlists UI logic out of `html_generation.py` into the consolidated `scripts/scripts.js` for cleaner structure and easier maintenance. The page still supports both compressed and plain table JSON.

### Added
- Two brand‑new Smart Playlists replacing the previous “Rising Obsessions” concept:
  - City Skyline Shuffle — Commute‑hour staples (7–9am, 4–6pm) that recur across different days; mid‑length focus; capped at 3 per artist for variety.
  - Late‑Bloomers — Slow‑burn risers across calendar quarters; increases over time without depending on the very latest month; capped at 3 per artist.

### Removed
- “Rising Obsessions: On the rise – you’ve been spinning these more this month.”

### Notes
- Seasonal Echoes remains computed at runtime in the browser each time you open the page and the playlists remain sorted alphabetically. The global filter that removes fully‑unknown items stays in effect.
