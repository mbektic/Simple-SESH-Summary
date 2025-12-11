"""
HTML generation module for Spotify Extended Streaming History.

This module contains functions for generating HTML content for the
Spotify Extended Streaming History summary report.
"""
import json
import logging
import re
import base64
import gzip
from typing import Dict, List, Any, DefaultDict


def ms_to_hms(ms: int) -> str:
    """
    Convert milliseconds to a formatted string with explicit units.

    Args:
        ms (int): Milliseconds to convert

    Returns:
        str: Formatted string in the format "HHh MMm SSs" (zero‑padded)
    """
    total_seconds = max(0, ms // 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}h {minutes:02}m {seconds:02}s"


def escape_js_string(s: str) -> str:
    """
    Escape special characters in a string for use in JavaScript template literals.

    Args:
        s (str): The string to escape

    Returns:
        str: The escaped string
    """
    return s.replace("\\", "\\\\").replace("`", "\\`")


def print_file(path: str) -> str:
    """
    Read and return the contents of a file.

    Args:
        path (str): Path to the file to read

    Returns:
        str: Contents of the file

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read due to permission issues.
    """
    try:
        with open(path, 'r', encoding='utf-8') as file:
            contents = file.read()
    except UnicodeDecodeError:
        # If utf-8 fails, you can fall back to 'utf-8-sig' or another encoding like 'latin-1'
        try:
            with open(path, 'r', encoding='utf-8-sig') as file:
                contents = file.read()
        except UnicodeDecodeError:
            # If utf-8-sig also fails, try latin-1 as a last resort
            logging.warning(f"Failed to decode {path} with utf-8 and utf-8-sig, trying latin-1")
            with open(path, 'r', encoding='latin-1') as file:
                contents = file.read()
    except (FileNotFoundError, PermissionError) as e:
        logging.error(f"Error reading file {path}: {e}")
        raise
    return contents


def minify_css(css: str) -> str:
    """
    Minify CSS safely:
    - Remove comments
    - Collapse whitespace
    - Remove unnecessary spaces around punctuation
    - Remove trailing semicolons before closing braces
    """
    try:
        # Remove /* */ comments
        css = re.sub(r"/\*[^!*][\s\S]*?\*/", "", css)
        # Collapse whitespace
        css = re.sub(r"\s+", " ", css)
        # Remove spaces around punctuation
        css = re.sub(r"\s*([{}:;,>])\s*", r"\1", css)
        # Remove trailing semicolons before }
        css = re.sub(r";\}", "}", css)
        # Trim
        return css.strip()
    except Exception:
        # On any failure, return original to be safe
        return css


def minify_js(js: str) -> str:
    """
    Conservatively minify JS:
    - Remove block comments (/* */)
    - Trim lines
    - Collapse multiple blank lines
    Does NOT remove // comments to avoid harming URLs inside strings.
    """
    try:
        # Remove block comments (but keep license /*! ... */)
        js = re.sub(r"/\*(?!\!)[\s\S]*?\*/", "", js)
        # Trim each line
        lines = [ln.strip() for ln in js.splitlines()]
        # Collapse consecutive empty lines to a single empty line
        out_lines: List[str] = []
        empty = 0
        for ln in lines:
            if ln == "":
                empty += 1
                if empty > 1:
                    continue
            else:
                empty = 0
            out_lines.append(ln)
        return "\n".join(out_lines).strip()
    except Exception:
        return js


def print_styles() -> str:
    """
    Read CSS files and return HTML style tags with the CSS content.

    Returns:
        str: HTML style tags and JavaScript constants with CSS content

    Raises:
        FileNotFoundError: If any of the CSS files cannot be found
    """
    try:
        base_style = minify_css(print_file("style/style.css"))
        dark_style = minify_css(print_file("style/dark.css"))
        light_style = minify_css(print_file("style/light.css"))

        return f"""
        <style id="base-style">{base_style}</style>
        <style id="theme-style">{dark_style}</style>
        <script>
            const DARK_CSS = `{escape_js_string(dark_style)}`;
            const LIGHT_CSS = `{escape_js_string(light_style)}`;
        </script>
        """
    except Exception as e:
        logging.error(f"Error loading CSS files: {e}")
        raise


def generate_js() -> str:
    """
    Generate JavaScript for the HTML page.

    Returns:
        str: JavaScript code as a string
    """
    js = print_file("scripts/scripts.js")
    js_min = minify_js(js)
    return f"""<script>{js_min}</script>"""


def predecode_script() -> str:
    """Return a small inline script that inflates base64-gzipped table data when supported.

    Important: we wait for DOMContentLoaded so the <script id="table-data-compressed"> element in the body exists
    before attempting to read and inflate it.
    """
    return (
        "<script>"
        "(function(){\n"
        "  function run(){\n"
        "    var cEl=document.getElementById('table-data-compressed');\n"
        "    if(!cEl){ if(!window.__TABLE_DATA_PROM) window.__TABLE_DATA_PROM = Promise.resolve(); return; }\n"
        "    var b64=cEl.textContent.trim();\n"
        "    function base64ToBytes(b64){var bin=atob(b64);var len=bin.length;var bytes=new Uint8Array(len);for(var i=0;i<len;i++){bytes[i]=bin.charCodeAt(i);}return bytes;}\n"
        "    function inflateWithDS(bytes){\n"
        "      var ds=new DecompressionStream('gzip');\n"
        "      var stream=new Response(new Blob([bytes]).stream().pipeThrough(ds));\n"
        "      return stream.arrayBuffer().then(function(buf){return new TextDecoder().decode(buf);});\n"
        "    }\n"
        "    window.__TABLE_DATA_PROM = (function(){\n"
        "      try{\n"
        "        var bytes=base64ToBytes(b64);\n"
        "        if(typeof DecompressionStream==='function'){\n"
        "          return inflateWithDS(bytes).then(function(txt){ window.__TABLE_DATA_CACHE = JSON.parse(txt); });\n"
        "        }\n"
        "      }catch(e){ console.error('Predecode failed', e); }\n"
        "      // Fallback: resolve immediately; main code will try #table-data (uncompressed) if present.\n"
        "      return Promise.resolve();\n"
        "    })();\n"
        "  }\n"
        "  if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded', run, {once:true}); } else { run(); }\n"
        "})();"
        "</script>"
    )


def build_table(title: str, playtime_counts: Dict[str, int], playcount_counts: Dict[str, int], table_id: str) -> str:
    """
    Build HTML tables for artists, tracks, or albums.

    Args:
        title (str): Title of the table
        playtime_counts (Dict[str, int]): Dictionary mapping names to playtime in milliseconds
        playcount_counts (Dict[str, int]): Dictionary mapping names to play counts
        table_id (str): ID for the table

    Returns:
        str: HTML table as a string
    """
    mode_string_playtime = "Playtime"
    mode_string_playcount = "Plays"

    # Data-first rendering: emit a single table skeleton; rows are rendered client-side from a JSON blob.
    # The third column label will be updated by JS based on the current mode (Playtime/Plays).
    return f"""
    <h2>{title}</h2>
    <input type=\"text\" id=\"{table_id}-search\" placeholder=\"Search for {title}...\" class=\"search-input\" />

    <div id=\"{table_id}-container\">
        <table data-title=\"{title}\">
            <thead><tr><th>Rank</th><th>{title}</th><th id=\"{table_id}-metric-label\">{mode_string_playtime}</th></tr></thead>
            <tbody id=\"{table_id}-tbody\"></tbody>
        </table>
    </div>

    <div class=\"pagination\" id=\"{table_id}-nav\"></div>
    """


def build_year_tabs(years: List[int]) -> str:
    """
    Build HTML for year tabs.

    Args:
        years (List[int]): List of years

    Returns:
        str: HTML for year tabs as a string
    """
    return '<button class="year-tab active" data-year="all" role="tab" aria-selected="true" aria-controls="year-all">All</button>' + "".join(
        f'<button class="year-tab" data-year="{yr}" role="tab" aria-selected="false" aria-controls="year-{yr}">{yr}</button>'
        for yr in years
    )


def build_year_dropdown(years: List[int]) -> str:
    """
    Build a mobile-friendly labeled dropdown for year selection.

    Args:
        years (List[int]): List of years

    Returns:
        str: HTML for a labeled <select> that mirrors the year tabs
    """
    options = '<option value="all" selected>All</option>' + "".join(
        f'<option value="{yr}">{yr}</option>' for yr in years
    )
    return f'''<div id="year-dropdown" class="year-dropdown" aria-label="Year selection">
  <label for="year-select" class="year-select-label">Year</label>
  <select id="year-select" class="year-select">{options}</select>
</div>'''


def build_all_section(all_data: Dict[str, DefaultDict[str, int]]) -> str:
    """
    Build HTML for the "All" section with tables for artists, tracks, and albums.

    Args:
        all_data (Dict[str, DefaultDict[str, int]]): Aggregated data for all years

    Returns:
        str: HTML for the "All" section as a string
    """
    sections = '<div class="year-section" id="year-all" style="display: block;">'
    sections += build_table("Artists",
                            all_data["artist_time"], all_data["artist_counts"],
                            "artist-table-all")
    sections += build_table("Tracks",
                            all_data["track_time"], all_data["track_counts"],
                            "track-table-all")
    sections += build_table("Albums",
                            all_data["album_time"], all_data["album_counts"],
                            "album-table-all")
    sections += "</div>"
    return sections


def build_tables_data(all_data: Dict[str, DefaultDict[str, int]],
                      yearly: DefaultDict[int, Dict[str, DefaultDict[str, int]]]) -> Dict[str, Any]:
    """
    Build a compact data structure for all tables to be rendered client-side.

    Returns a dictionary with two keys:
      - "names": a deduplicated list of all entity names (artists/tracks/albums)
      - "tables": a mapping of table_id -> list of [nameIndex, playtime_ms, playcount]

    Table IDs follow existing convention:
      - artist-table-all, track-table-all, album-table-all
      - artist-table-YYYY, track-table-YYYY, album-table-YYYY
    """
    tables: Dict[str, List[List[Any]]] = {}
    # Deduplicate names across all tables
    name_to_index: Dict[str, int] = {}
    names: List[str] = []

    def get_index(name: str) -> int:
        if name in name_to_index:
            return name_to_index[name]
        idx = len(names)
        name_to_index[name] = idx
        names.append(name)
        return idx

    def build_rows(name_to_ms: Dict[str, int], name_to_pc: Dict[str, int]) -> List[List[Any]]:
        rows_i: List[List[Any]] = []
        # Use union of keys to be safe (though both dicts should align)
        all_names = set(name_to_ms.keys()) | set(name_to_pc.keys())
        for nm in all_names:
            pt = int(name_to_ms.get(nm, 0))
            pc = int(name_to_pc.get(nm, 0))
            rows_i.append([get_index(nm), pt, pc])
        return rows_i

    # All-section tables
    tables["artist-table-all"] = build_rows(all_data["artist_time"], all_data["artist_counts"])
    tables["track-table-all"] = build_rows(all_data["track_time"], all_data["track_counts"])
    tables["album-table-all"] = build_rows(all_data["album_time"], all_data["album_counts"])

    # Per-year tables
    for yr, ydata in yearly.items():
        tables[f"artist-table-{yr}"] = build_rows(ydata["artist_time"], ydata["artist_counts"])
        tables[f"track-table-{yr}"] = build_rows(ydata["track_time"], ydata["track_counts"])
        tables[f"album-table-{yr}"] = build_rows(ydata["album_time"], ydata["album_counts"])

    return {"names": names, "tables": tables}


def build_year_sections(years: List[int]) -> str:
    """
    Build HTML for per-year sections with tables for artists, tracks, and albums.

    Args:
        years (List[int]): List of years

    Returns:
        str: HTML for per-year sections as a string
    """
    sections = ""
    for yr in years:
        sections += f'<div class="year-section" id="year-{yr}" style="display: none;"></div>'
    return sections


def build_stats_html(stats_data: Dict[str, Any], daily_counts: Dict[str, int], otd_data, yearly=None) -> str:
    """
    Build HTML for the statistics section.

    Args:
        stats_data (Dict[str, Any]): Dictionary containing statistics data

    Returns:
        str: HTML for the statistics section as a string
    """

    daily_counts_json = json.dumps({
        d.isoformat(): cnt
        for d, cnt in daily_counts.items()
    })
    first_date = stats_data.get('first_str', "")
    last_date = stats_data.get('last_str', "")

    # Build a simple per-year listening chart (playtime vs playcount) if yearly data provided
    year_chart_html = ""
    try:
        if yearly:
            years_sorted = sorted(yearly.keys())
            # Compute totals per year
            pt_totals = [sum(yearly[y]["track_time"].values()) for y in years_sorted]
            pc_totals = [sum(yearly[y]["track_counts"].values()) for y in years_sorted]
            max_pt = max(pt_totals) if pt_totals else 1
            max_pc = max(pc_totals) if pc_totals else 1

            # Build horizontal row markup with a full year label on the left and width‑scaled bars
            def build_horizontal_rows(values: list[int], max_val: int, include_pt: bool) -> str:
                rows = []
                for y, v_pc, v_pt in zip(years_sorted, pc_totals, pt_totals):
                    v = v_pt if include_pt else v_pc
                    # Scale so the maximum year maps to 90% width instead of 100%
                    width_pct = (v / (max_val if max_val else 1) * 90) if max_val > 0 else 0
                    # Guard against any floating rounding pushing it slightly above 90
                    if width_pct > 90:
                        width_pct = 90
                    # data attributes on the actual bar so tooltips can read current mode dynamically
                    rows.append(
                        """
                        <div class="yb-hrow">
                          <div class="yb-hlabel">{year}</div>
                          <div class="yb-hbar yb-bar" data-year="{year}" data-pc="{pc}" data-pt-ms="{pt}" style="width:{w:.2f}%;"></div>
                        </div>
                        """.format(year=y, pc=v_pc, pt=v_pt, w=width_pct)
                    )
                return "".join(rows)

            pc_rows_html = build_horizontal_rows(pc_totals, max_pc, include_pt=False)
            pt_rows_html = build_horizontal_rows(pt_totals, max_pt, include_pt=True)

            year_chart_html = (
                """
            <div id="listening-by-year" class="stats-group">
              <h3>Listening by Year</h3>
              <ul>
                <li>Hover/Tap on a year to see the exact values</li>
              </ul>
              <div class="yb-chart" aria-label="Listening by Year">
                <div id="year-chart-playcount" class="yb-series" style="display:none;">
                """ + pc_rows_html + """
                </div>
                <div id="year-chart-playtime" class="yb-series" style="display:flex;">
                """ + pt_rows_html + """
                </div>
              </div>
            </div>
            """
            )
    except Exception as e:
        logging.error(f"Failed to build yearly chart: {e}")

    return f"""
    <h2>Stats</h2>
    <div id="stats">
      <!-- 1. Overview & Time -->
      <div class="stats-group">
        <h3>Overview & Time</h3>
        <ul>
          <li>Days since first play: {stats_data['days_since_first']}</li>
          <li>Days played: {stats_data['days_played']} ({stats_data['pct_days']:.2f}%)</li>
          <li>First play: {stats_data['first_desc']}</li>
          <li>Last play: {stats_data['last_desc']}</li>
          <li>Total play: {stats_data['total_plays']}</li>
          <li>Total listening time: {stats_data['total_time_str']}</li>
          <li>Average playtime per play: {stats_data['avg_play_str']}</li>
        </ul>
      </div>

      <!-- 2. Library Stats -->
      <div class="stats-group">
        <h3>Library</h3>
        <ul>
          <li>Artists: {stats_data['artists_count']}</li>
          <li>One hit wonders: {stats_data['one_hits']} ({stats_data['pct_one_hits']:.2f}%)</li>
          <li>
            Every-year artists: {stats_data['every_year_count']}
            <button id="show-every-year-btn" class="stats-button">Show</button>
          </li>
          <li>Albums: {stats_data['albums_count']}</li>
          <li>Albums per artist: {stats_data['albums_per_artist']:.1f}</li>
          <li>Tracks: {stats_data['tracks_count']}</li>
          <li>Unique tracks ratio: {stats_data['unique_tracks']}/{stats_data['total_plays']} ({stats_data['unique_ratio_pct']:.2f}%)
            <button class="info-button stats-button" data-info="Unique Tracks ÷ Total Plays × 100">i</button>
          </li>
          <li>Gini coefficient: {stats_data['gini']:.3f}
            <button class="info-button stats-button" 
                    data-info="How evenly you spread listens across artists (0 = perfectly even, 1 = one artist).">i</button>
          </li>
        </ul>
      </div>

      <!-- 3. Milestones -->
      <div class="stats-group">
        <h3>Milestones</h3>
        <ul>
          <li>Eddington number: {stats_data['edd']}
             <button class="info-button stats-button"
                     data-info="This means you have {stats_data['edd']} days with at least {stats_data['edd']} plays.">i</button>
          </li>
          <li>Days to next Eddington ({stats_data['edd'] + 1}): {stats_data['next_need']}</li>
          <li>Artist cut-over point: {stats_data['art_cut']}
             <button class="info-button stats-button"
                     data-info="This means you have {stats_data['art_cut']} artists with at least {stats_data['art_cut']} plays.">i</button>
          </li>
        </ul>
      </div>

      <!-- 4. Popularity Records -->
      <div class="stats-group">
        <h3>Popularity</h3>
        <ul>
          <li>Most popular year: {stats_data['pop_year']} ({stats_data['pop_year_plays']} plays)</li>
          <li>Most popular month: {stats_data['pop_mon_str']} ({stats_data['pop_mon_plays']} plays)</li>
          <li>Most popular week: {stats_data['week_str']} ({stats_data['week_plays']} plays)</li>
          <li>Most popular day: {stats_data['day_str']} ({stats_data['day_plays']} plays)</li>
          <li>Most skipped track: {stats_data['most_skipped']} ({stats_data['skip_ct']} skips)</li>
        </ul>
      </div>

      <!-- 5. Listening Patterns -->
      <div class="stats-group">
        <h3>Patterns</h3>
        <ul>
          <li>Longest listening streak: {stats_data['max_streak']} days
             ({stats_data['streak_start'].strftime("%b %d, %Y")} – {stats_data['streak_end'].strftime("%b %d, %Y")})
          </li>
          <li>Longest hiatus: {stats_data['longest_hiatus']} days
             {f"({stats_data['hi_start_str']} – {stats_data['hi_end_str']})" if stats_data['longest_hiatus'] > 0 else ""}
          </li>
          <li>Average plays per active day: {stats_data['avg_plays']:.2f}</li>
          <li>Most active weekday: {stats_data['wd_name']} ({stats_data['wd_count']} plays)</li>
          <li>Peak listening hour: {stats_data['peak_hour_str']} ({stats_data['hour_count']} plays)</li>
          <li>Weekend vs Weekday plays: {stats_data['weekend']}/{stats_data['weekday']} ({stats_data['ratio_pct']:.2f}% weekend)</li>
        </ul>
      </div>

      <!-- 6. Sessions & Behavior -->
      <div class="stats-group">
        <h3>Sessions & Behavior</h3>
        <ul>
          <li>Number of sessions: {stats_data['num_sessions']}
             <button class="info-button stats-button"
                     data-info='A "session" is consecutive plays with <30 min gaps.'>i</button>
          </li>
          <li>Average session length: {stats_data['avg_str']}</li>
          <li>Longest single session: {stats_data['long_str']} on {stats_data['long_date_str']}</li>
          <li>Skip rate: {stats_data['skip_count']}/{stats_data['play_counted']} ({stats_data['skip_rate_pct']:.2f}%)</li>
          <li>Offline vs Online ratio: {stats_data['ratio_str']} ({stats_data['offline_ratio_pct']:.2f}% offline)</li>
        </ul>
      </div>

    <div id="" class="stats-group">
        <h3>On This Day <input type="date" id="otd-date" /></h3>
        <div id="otd-results"></div>
        <div id="otd-pagination" class="otd-pagination">
          <button id="otd-prev" class="stats-button">Prev</button>
          <span id="otd-page-label"></span>
          <button id="otd-next" class="stats-button">Next</button>
        </div>
      </div>
    </div>


     <!-- hidden modal -->
    <div id="every-year-modal" class="modal-overlay" style="display:none;" role="dialog" aria-modal="true" aria-labelledby="every-year-title" aria-hidden="true">
      <div class="modal-content">
        <div class="modal-header">
            <h2 id="every-year-title">Artists played every year({stats_data['every_year_count']})</h2>
            <button id="close-every-year-modal" class="close-button" aria-label="Close artists list">&times;</button>
        </div>
        <ul style="list-style:none; padding:0; margin-top:1em; max-height:60vh; overflow:auto;" role="list" aria-label="Artists played every year">
          {"".join(f"<li>{a}</li>" for a in stats_data['every_year_list'])}
        </ul>
      </div>
    </div>
    
      {year_chart_html}

      <div id="heatmap-holder" class="stats-group">
        <h3>Activity Heatmap</h3>
        <div id="calendar-heatmap"></div>
        <div class="heatmap-legend">
          <span>Less</span>
          <div class="heatmap-cell level-0"></div>
          <div class="heatmap-cell level-1"></div>
          <div class="heatmap-cell level-2"></div>
          <div class="heatmap-cell level-3"></div>
          <div class="heatmap-cell level-4"></div>
          <span>More</span>
        </div>
      </div>


      <script>{print_file("scripts/popper.min.js")}</script>
      <script>{print_file("scripts/tippy-bundle.umd.min.js")}</script>
      <script>
        const startDate = new Date("{first_date}");
        const endDate   = new Date("{last_date}");
        const counts = JSON.parse(`{daily_counts_json}`);
        const onThisDayData = {otd_data};
        {print_file("scripts/heatmap.js")}
        {print_file("scripts/otd.js")}
      </script>
    """


def generate_personality_html(stats_data: Dict[str, Any]) -> str:
    """
    Generate HTML for the personality type section.

    Args:
        stats_data (Dict[str, Any]): Dictionary containing statistics data

    Returns:
        str: HTML for the personality type section
    """
    personality_type = stats_data.get('personality_type', 'Undefined')
    personality_desc = stats_data.get('personality_desc', 'Your listening style is unique.')
    personality_percentages = stats_data.get('personality_percentages', {})

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

    # Sort personality types by percentage (descending)
    sorted_types = sorted(personality_percentages.items(), key=lambda x: x[1], reverse=True)
    max_percentage = max((v for v in personality_percentages.values()), default=1)  # Avoid division by 0

    bars_html = ""
    for ptype, percentage in sorted_types:
        rounded_percentage = round(percentage, 1)
        scaled_width = max(5, (percentage / max_percentage) * 100)  # Ensure visibility

        highlight_class = "primary-type" if ptype == personality_type else ""
        description = descriptions.get(ptype, "A unique listening style.")

        bars_html += f"""
        <div class="personality-bar-container" data-tippy-content="{description}">
            <div class="personality-type-label">{ptype}</div>
            <div class="personality-bar-wrapper">
                <div class="personality-bar {highlight_class}" style="width: {scaled_width:.1f}%"></div>
                <div class="personality-percentage">{rounded_percentage}%</div>
            </div>
        </div>
        """

    return f"""
    <h2>Your Listening Personality Type: <span style="color: #1DB954;">{personality_type}</span></h2>
    <div id="personality-type" class="stats-group">
        <p>{personality_desc}</p>
        <div class="personality-chart">
            {bars_html}
        </div>
    </div>
    """


def generate_html_content(tabs: str, sections: str, stats_html: str, github_url: str, version: str,
                          personality_html: str, year_dropdown: str = "",
                          table_data: Dict[str, List[List[Any]]] | None = None,
                          compress: bool | None = None) -> str:
    """
    Generate the complete HTML content for the summary report.

    Args:
        tabs (str): HTML for year tabs
        sections (str): HTML for year sections
        stats_html (str): HTML for statistics
        github_url (str): URL to the GitHub repository
        version (str): Version of the application
        personality_html (str): HTML for the personality type section

    Returns:
        str: Complete HTML content as a string
    """
    data_script = ""
    try:
        if table_data is not None:
            # Decide compression
            do_compress = False
            if compress is not None:
                do_compress = compress
            else:
                try:
                    from config import COMPRESS_TABLE_DATA as _CTD
                    do_compress = bool(_CTD)
                except Exception:
                    do_compress = False

            if do_compress:
                try:
                    json_str = json.dumps(table_data, separators=(",", ":"))
                    b = json_str.encode('utf-8')
                    gz = gzip.compress(b)
                    b64 = base64.b64encode(gz).decode('ascii')
                    data_script = f"""
        <script id=\"table-data-compressed\" type=\"application/json\">{b64}</script>
                    """
                except Exception as e:
                    logging.error(f"Compression failed, falling back to plain JSON: {e}")
                    data_script = f"""
        <script id=\"table-data\" type=\"application/json\">{json.dumps(table_data)}</script>
                    """
            else:
                data_script = f"""
        <script id=\"table-data\" type=\"application/json\">{json.dumps(table_data)}</script>
                """
    except Exception as e:
        logging.error(f"Failed to serialize table data: {e}")

    return f"""
    <!DOCTYPE html>
    <html style='overflow: hidden;'>
    <head>
        <meta charset="UTF-8">
        <title>Spotify Summary</title>
        <link href='https://fonts.googleapis.com/css?family=JetBrains Mono' rel='stylesheet'>
        {print_styles()}
        {predecode_script()}
        {generate_js()}
    </head>
    <body style='overflow: hidden;'>
        {print_file("html/title_bar.html")}
        <div id="year-tabs">{tabs}</div>
        {year_dropdown}
        {data_script}
        {sections}
        {personality_html}
        {stats_html}

        {print_file("html/settings_modal.html")}
    </body>
    <footer>
      <a id="version-link" href="{github_url}">Version: {version}</a>
    </footer>
    </html>
    """


def minify_html(html: str) -> str:
    """
    Minify HTML string while preserving content inside <script> and <style> tags.

    - Removes HTML comments
    - Collapses redundant whitespace and newlines
    - Removes whitespace between tags

    Args:
        html (str): Raw HTML content

    Returns:
        str: Minified HTML content
    """
    # Split by blocks to preserve exact contents for tags that are whitespace-sensitive
    pattern = re.compile(r"(?is)(<script\b[^>]*?>.*?</script>|<style\b[^>]*?>.*?</style>|<pre\b[^>]*?>.*?</pre>|<textarea\b[^>]*?>.*?</textarea>)")
    parts = []
    last = 0
    for m in pattern.finditer(html):
        # Process preceding non-script/style chunk
        head = html[last:m.start()]
        if head:
            # Remove comments
            head = re.sub(r"<!--.*?-->", "", head, flags=re.S)
            # Collapse whitespace
            head = re.sub(r"\s+", " ", head)
            # Remove spaces between tags
            head = re.sub(r">\s+<", "><", head)
            head = head.strip()
            parts.append(head)
        # Append the script/style block unchanged
        parts.append(m.group(1))
        last = m.end()

    # Process trailing chunk
    tail = html[last:]
    if tail:
        tail = re.sub(r"<!--.*?-->", "", tail, flags=re.S)
        tail = re.sub(r"\s+", " ", tail)
        tail = re.sub(r">\s+<", "><", tail)
        tail = tail.strip()
        parts.append(tail)

    return "".join(parts)


def write_html_to_file(html_content: str, output_file: str) -> None:
    """
    Write HTML content to a file.

    Args:
        html_content (str): HTML content to write
        output_file (str): Path to the output file

    Raises:
        IOError: If the file cannot be written
        PermissionError: If the file cannot be written due to permission issues
    """
    try:
        # Minify the final HTML output while keeping source files unmodified
        minimized = minify_html(html_content)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(minimized)
        logging.info(f"✅ HTML report generated: {output_file}")
    except (IOError, PermissionError) as e:
        logging.error(f"Failed to write HTML report to {output_file}: {e}")
        raise
