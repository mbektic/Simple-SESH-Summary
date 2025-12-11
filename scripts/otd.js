const TRACKS_PER_PAGE = 5;
let currentPage = 0;
let currentList = [];

// Lazy-built cache: MM-DD -> Array<{track, date, count}>
let __OTD_CACHE = null;

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

    document.getElementById("otd-results").innerHTML = `
    <ol class="otd-list">
      ${slice.map(({track, date, count}) => `
        <li>
          <span class="otd-track">${track}</span>
          <span class="otd-meta">${count}× on ${new Date(date + 'T12:00:00Z').toLocaleDateString()}</span>
        </li>
      `).join("")}
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