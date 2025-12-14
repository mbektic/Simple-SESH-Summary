const TRACKS_PER_PAGE = 5;
let currentPage = 0;
let currentList = [];

// Lazy-built cache: MM-DD -> Array<{track, date, count}>
let __OTD_CACHE = null;

// Build a Spotify link for a given track using search (works without URIs)
function spotifySearchLink(track) {
    try {
        const q = String(track || '').trim();
        if (!q) return 'https://open.spotify.com/search';
        return 'https://open.spotify.com/search/' + encodeURIComponent(q);
    } catch (_) {
        return 'https://open.spotify.com/search';
    }
}

// Prefer direct track URLs when we can infer a Spotify URI from Smart Playlists
// Use window-scoped singletons to avoid "redeclaration" across concatenated scripts

function getPlaylistsData() {
    if (window.__PLAYLISTS_DATA_CACHE) return window.__PLAYLISTS_DATA_CACHE;
    try {
        const el = document.getElementById('smart-playlists');
        if (!el) return null;
        window.__PLAYLISTS_DATA_CACHE = JSON.parse(el.textContent);
        return window.__PLAYLISTS_DATA_CACHE;
    } catch (e) {
        // ignore parse errors
        return null;
    }
}

function getTrackUriMap() {
    if (window.__TRACK_URI_MAP) return window.__TRACK_URI_MAP;
    window.__TRACK_URI_MAP = {};
    const norm = (s) => String(s || '')
        .toLowerCase()
        .replace(/[\u2012\u2013\u2014\u2015]/g, '-')
        .replace(/\s*[-–—]\s*/g, ' - ')
        .replace(/\s+/g, ' ')
        .trim();
    const put = (k, uri) => { if (k && uri && !window.__TRACK_URI_MAP[k]) window.__TRACK_URI_MAP[k] = uri; };

    // 1) Seed from table-data (preferred)
    try {
        const root = getTableData();
        const namesArr = Array.isArray(root && root.names) ? root.names : [];
        const urisArr = Array.isArray(root && root.uris) ? root.uris : [];
        for (let i = 0; i < namesArr.length && i < urisArr.length; i++) {
            const name = String(namesArr[i] || '').trim();
            const uri = String(urisArr[i] || '');
            if (!name || !uri || !uri.startsWith('spotify:track:')) continue;
            put(norm(name), uri);
            const parts = name.split(/\s*[\-\u2012\u2013\u2014\u2015]\s+/);
            if (parts.length >= 2) put(norm(parts[0]), uri);
        }
    } catch (e) { /* ignore */ }

    // 2) Merge Smart Playlists without overwriting
    const data = getPlaylistsData();
    try {
        const pls = data && Array.isArray(data.playlists) ? data.playlists : [];
        pls.forEach(pl => {
            const items = Array.isArray(pl.items) ? pl.items : [];
            items.forEach(it => {
                const name = (it && it.track) ? String(it.track).trim() : '';
                const artist = (it && it.artist) ? String(it.artist).trim() : '';
                const uri = it && it.uri ? String(it.uri) : '';
                if (!name || !uri || !uri.startsWith('spotify:track:')) return;
                put(norm(name), uri);
                if (artist) {
                    put(norm(name + ' - ' + artist), uri);
                    put(norm(name + ' — ' + artist), uri);
                }
            });
        });
    } catch (e) { /* ignore */ }
    return window.__TRACK_URI_MAP;
}

function spotifyLinkForName(trackName) {
    try {
        const raw = String(trackName || '').trim();
        if (!raw) return '';
        const map = getTrackUriMap();
        const norm = (s) => String(s || '')
            .toLowerCase()
            .replace(/[\u2012\u2013\u2014\u2015]/g, '-')
            .replace(/\s*[-–—]\s*/g, ' - ')
            .replace(/\s+/g, ' ')
            .trim();

        // Try exact match on the full label (handles "Track - Artist")
        let uri = map[norm(raw)];
        if (!uri) {
            // Try splitting into track and artist and look up aliases
            const split = raw.split(/\s*[\-\u2012\u2013\u2014\u2015]\s+/);
            if (split.length >= 2) {
                const track = split[0];
                const artist = split.slice(1).join(' - ');
                uri = map[norm(track + ' - ' + artist)] || map[norm(track)];
            } else {
                uri = map[norm(raw)];
            }
        }
        if (uri && uri.startsWith('spotify:track:')) {
            const id = uri.split(':').pop();
            return 'https://open.spotify.com/track/' + encodeURIComponent(id);
        }
        // No search fallback: only return a direct track URL if we have an ID
        return '';
    } catch (_) {
        return '';
    }
}

function buildOTDCache(force = false) {
    // Allow explicit rebuilds
    if (force) __OTD_CACHE = null;
    if (__OTD_CACHE) return __OTD_CACHE;

    let out = {};
    try {
        const data = getTableData();
        if (!data || typeof data !== 'object') return out;

        const names = Array.isArray(data.names) ? data.names : [];
        const daily = data.daily || {};

        const dates = Object.keys(daily);
        if (!dates.length) return out; // Data not ready yet (e.g., waiting for decompression)

        // daily has shape: { 'YYYY-MM-DD': { track: Array[[nameIndex, pt, pc]], ... } }
        for (const date of dates) {
            const mmdd = date.slice(5, 10);
            const groups = daily[date] || {};
            const trackRows = Array.isArray(groups.track) ? groups.track : [];
            for (const row of trackRows) {
                // row: [nameIndex, pt, pc]
                const idx = row[0];
                const pc = row[2] || 0;
                if (pc > 2 && idx != null && names[idx] != null) {
                    if (!out[mmdd]) out[mmdd] = [];
                    out[mmdd].push({
                        track: names[idx],
                        date: date,
                        count: pc
                    });
                }
            }
        }
    } catch (e) {
        console.error('Failed to build On This Day cache', e);
    }

    // Only memoize if we actually built something (prevents caching an empty map before data is ready)
    if (Object.keys(out).length) {
        __OTD_CACHE = out;
        return __OTD_CACHE;
    }
    return out;
}

function renderOTDPage() {
    const start = currentPage * TRACKS_PER_PAGE;
    const end = start + TRACKS_PER_PAGE;
    const slice = currentList.slice(start, end);

    const html = slice.map(({track, date, count}) => {
        const link = (window.spotifyLinkForName || spotifyLinkForName)(track);
        const label = track;
        const dateStr = new Date(date + 'T12:00:00Z').toLocaleDateString();
        if (link) {
            return `
        <li>
          <a class="otd-track" href="${link}" target="_blank" rel="noopener noreferrer">${label}</a>
          <span class="otd-meta">${count}× on ${dateStr}</span>
        </li>`;
        }
        return `
        <li>
          <span class="otd-track">${label}</span>
          <span class="otd-meta">${count}× on ${dateStr}</span>
        </li>`;
    }).join("");

    document.getElementById("otd-results").innerHTML = `
    <ol class="otd-list" start="${start + 1}">
      ${html}
    </ol>
  `;

    const pageLabel = document.getElementById("otd-page-label");
    const totalPages = Math.ceil(currentList.length / TRACKS_PER_PAGE);
    pageLabel.textContent = `Page ${currentPage + 1} of ${totalPages}`;

    document.getElementById("otd-prev").disabled = currentPage === 0;
    document.getElementById("otd-next").disabled = currentPage >= totalPages - 1;
}

function renderOTD(dateStr) {
    const mmdd = dateStr.slice(5, 10);
    const cache = buildOTDCache();
    currentList = cache[mmdd] || [];

    if (!currentList.length) {
        document.getElementById("otd-results").innerHTML = `<p>No songs were played more than 2x on this day in past years.</p>`;
        document.getElementById("otd-pagination").style.display = "none";
        return;
    }

    currentList.sort((a, b) => b.count - a.count);

    currentPage = 0;
    const totalPages = Math.ceil(currentList.length / TRACKS_PER_PAGE);
    document.getElementById("otd-pagination").style.display = totalPages > 1 ? "block" : "none";

    renderOTDPage();
}

// Initialization
document.addEventListener("DOMContentLoaded", () => {
    function todayLocalISO() {
        const d = new Date();
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    }

    const init = () => {
        const input = document.getElementById("otd-date");
        const today = todayLocalISO();
        input.value = today;
        // Force a rebuild now that data should be ready (no-op if uncompressed path)
        buildOTDCache(true);
        renderOTD(today);

        input.addEventListener("change", e => {
            renderOTD(e.target.value);
        });

        document.getElementById("otd-prev").addEventListener("click", () => {
            if (currentPage > 0) {
                currentPage--;
                renderOTDPage();
            }
        });

        document.getElementById("otd-next").addEventListener("click", () => {
            if ((currentPage + 1) * TRACKS_PER_PAGE < currentList.length) {
                currentPage++;
                renderOTDPage();
            }
        });
    };

    try {
        const prom = window.__TABLE_DATA_PROM;
        if (prom && typeof prom.then === 'function') {
            prom.then(init).catch(init);
        } else {
            init();
        }
    } catch (e) {
        // Fall back to immediate init if anything goes wrong
        init();
    }
});