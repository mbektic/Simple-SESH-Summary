const themeStyle = document.getElementById("theme-style");
const currentTheme = localStorage.getItem("theme") || "dark";
themeStyle.textContent = currentTheme === "dark" ? DARK_CSS : LIGHT_CSS;
let __TABLE_DATA_CACHE = null;
function getTableData() {
    try {
        // Prefer the globally decompressed cache when compression is enabled
        if (window.__TABLE_DATA_CACHE && typeof window.__TABLE_DATA_CACHE === 'object') {
            __TABLE_DATA_CACHE = window.__TABLE_DATA_CACHE;
            return __TABLE_DATA_CACHE;
        }

        // If we've already populated a local cache (uncompressed path), return it
        if (__TABLE_DATA_CACHE !== null) return __TABLE_DATA_CACHE;

        // Fallback: uncompressed inline JSON
        const el = document.getElementById('table-data');
        if (el) {
            __TABLE_DATA_CACHE = JSON.parse(el.textContent);
            return __TABLE_DATA_CACHE;
        }

        // If compressed node exists but global cache isn't ready yet, return empty object for now
        const cel = document.getElementById('table-data-compressed');
        if (cel) {
            console.debug('Waiting for compressed table data to be inflated…');
        }
        __TABLE_DATA_CACHE = {};
        return __TABLE_DATA_CACHE;
    } catch (e) {
        console.error('Failed to obtain table data', e);
        __TABLE_DATA_CACHE = {};
        return __TABLE_DATA_CACHE;
    }
}

// Normalize table data to a root object with shape:
//   { names: string[] | null, tables: { [tableId]: Array<[nameIndexOrString, pt, pc]> } }
function getTableRoot() {
    const raw = getTableData();
    if (raw && typeof raw === 'object' && raw.names && raw.tables) {
        return raw; // new compact format
    }
    // fallback: legacy flat map of tableId -> Array<[name, pt, pc]>
    return { names: null, tables: (raw || {}) };
}
const searchTerms = {};
let itemsPerPage = parseInt(localStorage.getItem("itemsPerPage"), 5) || 5;

function formatMs(ms){
    const sec = Math.floor(ms/1000);
    const h = Math.floor(sec/3600);
    const m = Math.floor((sec%3600)/60);
    const s = sec%60;
    const pad = (n) => n.toString().padStart(2, '0');
    return `${pad(h)}h ${pad(m)}m ${pad(s)}s`;
}

window.onload = () => {
    const overlay = document.getElementById('loading-overlay');

    function initVisible() {
        // Initialize only the visible section to keep first paint fast
        const visible = Array.from(document.querySelectorAll('.year-section')).find(sec => sec.style.display !== 'none');
        if (visible) {
            const yr = visible.id.split('-')[1];
            ['artist-table','track-table','album-table'].forEach(base =>
                paginateTable(`${base}-${yr}`, itemsPerPage)
            );
        }
    }

    requestAnimationFrame(() => {
        const prom = window.__TABLE_DATA_PROM;
        if (prom && typeof prom.then === 'function') {
            prom.finally(() => initVisible());
        } else {
            initVisible();
        }

        // Trigger the fade-out
        overlay.classList.add('fade-out');

        // Re-enable scrolling after fade-out transition
        overlay.addEventListener('transitionend', () => {
            document.body.style.overflow = '';
            document.documentElement.style.overflow = '';
        }, {once: true});
    });
};

// Ensure a lazily-loaded year section has its table skeletons
function ensureYearSection(year) {
    if (year === 'all') return; // 'All' is server-rendered
    const section = document.getElementById(`year-${year}`);
    if (!section) return;
    if (section.__initialized) return;
    // If already has children, assume initialized
    if (section.children && section.children.length > 0) {
        section.__initialized = true;
        return;
    }
    const blocks = [
        {base: 'artist-table', title: 'Artists'},
        {base: 'track-table', title: 'Tracks'},
        {base: 'album-table', title: 'Albums'}
    ];
    let html = '';
    blocks.forEach(({base, title}) => {
        const tableId = `${base}-${year}`;
        html += `
    <h2>${title}</h2>
    <input type="text" id="${tableId}-search" placeholder="Search for ${title}..." class="search-input" />
    <div id="${tableId}-container">
        <table data-title="${title}">
            <thead><tr><th>Rank</th><th>${title}</th><th id="${tableId}-metric-label">Playtime</th></tr></thead>
            <tbody id="${tableId}-tbody"></tbody>
        </table>
    </div>
    <div class="pagination" id="${tableId}-nav"></div>`;
    });
    section.innerHTML = html;
    section.__initialized = true;
}

function paginateTable(tableId, pageSize) {
    const isPlaytime = document.getElementById('global-mode-toggle')?.checked;
    const tbody = document.getElementById(`${tableId}-tbody`);
    const metricLabel = document.getElementById(`${tableId}-metric-label`);
    const searchInput = document.getElementById(`${tableId}-search`);
    const prefix = tableId.replace(/-(?:\d{4}|all|custom)$/,'');
    const root = getTableRoot();
    const namesArr = root.names; // may be null in legacy format
    const rawRows = (root.tables && root.tables[tableId]) ? root.tables[tableId] : [];

    if (!tbody) return;
    if (metricLabel) metricLabel.textContent = isPlaytime ? 'Playtime' : 'Plays';

    // Sort by current mode desc
    const sortedIdx = Array.from({length: rawRows.length}, (_, i) => i).sort((ia, ib) => {
        const a = rawRows[ia], b = rawRows[ib];
        const va = isPlaytime ? a[1] : a[2];
        const vb = isPlaytime ? b[1] : b[2];
        return vb - va;
    });

    const term = (searchTerms[prefix] ?? searchInput?.value ?? '').toLowerCase();
    const filteredIdx = term
        ? sortedIdx.filter(i => {
            const row = rawRows[i];
            const n = row && row.length ? row[0] : '';
            const nameStr = (namesArr && typeof n === 'number') ? (namesArr[n] || '') : (n || '');
            return nameStr.toLowerCase().includes(term);
        })
        : sortedIdx;

    let currentPage = 1;

    function renderPage(page){
        currentPage = page;
        const start = (page - 1) * pageSize;
        const end = page * pageSize;
        const frag = document.createDocumentFragment();

        const sliceIdx = filteredIdx.slice(start, end);
        if (sliceIdx.length === 0) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 3;
            td.style.height = '300px';
            td.style.textAlign = 'center';
            td.textContent = 'No results found.';
            tr.appendChild(td);
            frag.appendChild(tr);
        } else {
            sliceIdx.forEach((ri, idx) => {
                const row = rawRows[ri] || [];
                const n = row[0];
                const pt = row[1] || 0;
                const pc = row[2] || 0;
                const name = (namesArr && typeof n === 'number') ? (namesArr[n] || '') : (n || '');
                const tr = document.createElement('tr');
                const tdRank = document.createElement('td');
                const tdName = document.createElement('td');
                const tdVal = document.createElement('td');
                tdRank.textContent = String(start + idx + 1);
                if (term) {
                    const re = new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
                    tdName.innerHTML = name.replace(re, '<span class="highlight">$1</span>');
                } else {
                    tdName.textContent = name;
                }
                tdVal.textContent = isPlaytime ? formatMs(pt) : String(pc);
                tr.appendChild(tdRank);
                tr.appendChild(tdName);
                tr.appendChild(tdVal);
                frag.appendChild(tr);
            });
        }

        tbody.innerHTML = '';
        tbody.appendChild(frag);
        requestAnimationFrame(renderPagination);
    }

    function renderPagination(){
        const totalPages = Math.max(1, Math.ceil(filteredIdx.length / pageSize));
        const nav = document.getElementById(`${tableId}-nav`);
        if (!nav) return;
        nav.innerHTML = '';
        function createButton(label, page, active=false, disabled=false){
            const btn = document.createElement('button');
            btn.textContent = label;
            if (active) btn.classList.add('active');
            if (disabled) btn.disabled = true;
            btn.onclick = () => renderPage(page);
            nav.appendChild(btn);
        }
        createButton('Prev', currentPage - 1, false, currentPage === 1);
        const pageWindow = 1;
        const startPage = Math.max(1, currentPage - pageWindow);
        const endPage = Math.min(totalPages, currentPage + pageWindow);
        if (startPage > 1) {
            createButton('1', 1);
            if (startPage > 2) nav.appendChild(document.createTextNode('...'));
        }
        for (let i = startPage; i <= endPage; i++) createButton(String(i), i, i === currentPage);
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) nav.appendChild(document.createTextNode('...'));
            createButton(String(totalPages), totalPages);
        }
        createButton('Next', currentPage + 1, false, currentPage === totalPages);
    }

    if (searchInput && !searchInput.__wired) {
        searchInput.__wired = true;
        searchInput.addEventListener('input', () => {
            searchTerms[prefix] = searchInput.value;
            renderPage(1);
        });
    }

    renderPage(1);
}

document.addEventListener("DOMContentLoaded", () => {
    // Theme mode toggle
    const toggle = document.getElementById("theme-toggle");
    toggle.checked = currentTheme === "dark";

    toggle.addEventListener("change", () => {
        const isDark = toggle.checked;
        themeStyle.textContent = isDark ? DARK_CSS : LIGHT_CSS;
        localStorage.setItem("theme", isDark ? "dark" : "light");
    });

    // Global mode toggle
    const modeToggle = document.getElementById("global-mode-toggle");
    const modeToggleText = document.getElementById(`mode-toggle-label`);
    // Initialize yearly chart to current mode if available
    const initialMode = modeToggle.checked ? "playtime" : "playcount";
    // Define and expose yearly chart mode switcher + tooltips
    (function(){
        function formatMs(ms){
            const sec = Math.floor(ms/1000);
            const h = Math.floor(sec/3600);
            const m = Math.floor((sec%3600)/60);
            const s = sec%60;
            const pad = (n) => n.toString().padStart(2, '0');
            return `${pad(h)}h ${pad(m)}m ${pad(s)}s`;
        }

        function getYearBarTooltip(reference){
            const year = reference.getAttribute('data-year');
            const isPlaytime = document.getElementById('global-mode-toggle').checked;
            if (isPlaytime) {
                const ms = parseInt(reference.getAttribute('data-pt-ms')||'0',10);
                return `${year}: ${formatMs(ms)}`;
            } else {
                const pc = parseInt(reference.getAttribute('data-pc')||'0',10);
                return `${year}: ${pc} plays`;
            }
        }

        // initialize tippy on bars with dynamic content based on current mode
        function initYearBarTooltips(){
            tippy('.yb-bar', {
                onShow(instance){
                    instance.setContent(getYearBarTooltip(instance.reference));
                },
                allowHTML: false,
                placement: 'top',
                arrow: true,
                theme: 'spotify',
                maxWidth: '50em'
            });
        }

        function setYearChart(mode){
            const pc = document.getElementById('year-chart-playcount');
            const pt = document.getElementById('year-chart-playtime');
            if(!pc || !pt) return;
            if(mode === 'playcount'){ pc.style.display='flex'; pt.style.display='none'; }
            else { pc.style.display='none'; pt.style.display='flex'; }
            // No need to recreate tippy; content is dynamic and uses current mode
        }

        function refreshYearBarTooltips(){
            document.querySelectorAll('.yb-bar').forEach(el => {
                if (el._tippy) {
                    el._tippy.setContent(getYearBarTooltip(el));
                }
            });
        }

        window.__setYearChartMode = setYearChart;
        // Initialize now
        setYearChart(initialMode);
        initYearBarTooltips();
        // Ensure initial tooltip content matches initial mode
        refreshYearBarTooltips();
    })();
    modeToggle.addEventListener("change", () => {
        const newMode = modeToggle.checked ? "playtime" : "playcount";

        // Re-render only the currently visible section's tables in the new mode
        const visible = Array.from(document.querySelectorAll('.year-section')).find(sec => sec.style.display !== 'none');
        if (visible) {
            const yr = visible.id.split('-')[1];
            ["artist-table", "track-table", "album-table"].forEach(base => {
                paginateTable(`${base}-${yr}`, itemsPerPage);
            });
        }

        modeToggleText.textContent = modeToggle.checked
            ? "Switch to Playcount:"
            : "Switch to Playtime:";

        // Update yearly chart dataset if present
        if (typeof window.__setYearChartMode === 'function') {
            window.__setYearChartMode(newMode);
        }
        // Refresh tooltip content to reflect the new mode immediately
        document.querySelectorAll('.yb-bar').forEach(el => {
            if (el._tippy) {
                // Update content; if a tooltip is open, this updates live
                el._tippy.setContent((function(){
                    const year = el.getAttribute('data-year');
                    if (newMode === 'playtime') {
                        const ms = parseInt(el.getAttribute('data-pt-ms')||'0',10);
                        return `${year}: ${formatMs(ms)}`;
                    } else {
                        const pc = parseInt(el.getAttribute('data-pc')||'0',10);
                        return `${year}: ${pc} plays`;
                    }
                })());
            }
        });
    });
})


function switchMode(tableId, mode) {
    // Data-first rendering: simply re-render the table for the given id
    paginateTable(tableId, itemsPerPage);
}

// Modal utility functions
function setupFocusTrap(modalElement) {
    const focusableElements = modalElement.querySelectorAll(
        'a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Handle tab key to trap focus
    modalElement.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            // Shift + Tab
            if (e.shiftKey && document.activeElement === firstElement) {
                e.preventDefault();
                lastElement.focus();
            }
            // Tab
            else if (!e.shiftKey && document.activeElement === lastElement) {
                e.preventDefault();
                firstElement.focus();
            }
        }
    });
}

function openModal(modal, opener) {
    modal.style.display = "flex";
    modal.dataset.opener = opener.id || '';

    // Focus the first focusable element
    const firstFocusable = modal.querySelector('a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])');
    if (firstFocusable) {
        setTimeout(() => firstFocusable.focus(), 50);
    }
}

function closeModal(modal) {
    if (modal.style.display !== "flex") return;

    modal.style.display = "none";

    // Return focus to the opener element
    const openerId = modal.dataset.opener;
    if (openerId) {
        const opener = document.getElementById(openerId);
        if (opener) opener.focus();
    }
}

function setupModal(modalId, openerId, closeButtonId) {
    const modal = document.getElementById(modalId);
    const opener = document.getElementById(openerId);
    const closeButton = document.getElementById(closeButtonId);

    setupFocusTrap(modal);

    if (opener) {
        opener.addEventListener("click", () => openModal(modal, opener));
    }

    if (closeButton) {
        closeButton.addEventListener("click", () => closeModal(modal));
    }

    // Close modal if clicked outside
    modal.addEventListener("click", (e) => {
        if (e.target === modal) {
            closeModal(modal);
        }
    });

    return {modal, opener, closeButton};
}

document.addEventListener("DOMContentLoaded", () => {
    // Set up all modals
    const {modal: settingsModal} = setupModal("settings-modal", "settings-button", "close-settings");
    const {modal: everyYearModal} = setupModal("every-year-modal", "show-every-year-btn", "close-every-year-modal");
    const {modal: dateRangeModal} = setupModal("date-range-modal", null, "close-date-range");

    // Wire date range modal extra buttons
    const applyDateBtn = document.getElementById('apply-date-range');
    const cancelDateBtn = document.getElementById('cancel-date-range');
    const startInput = document.getElementById('date-start-input');
    const endInput = document.getElementById('date-end-input');
    let __pendingCustomActivate = null; // which tab or select triggered the modal

    function getDailyRoot(){
        const root = getTableRoot();
        return (root && root.daily) ? root : null;
    }

    function getDailyBounds(){
        const r = getDailyRoot();
        if (!r) return {min: null, max: null};
        const keys = Object.keys(r.daily).sort();
        return {min: keys[0] || null, max: keys[keys.length-1] || null};
    }

    function openDateRangeModal(openerEl){
        // Prefill inputs with last used or data bounds
        const saved = JSON.parse(localStorage.getItem('customRange')||'{}');
        const bounds = getDailyBounds();
        startInput.value = saved.start || bounds.min || '';
        endInput.value = saved.end || bounds.max || '';
        __pendingCustomActivate = openerEl || null;
        openModal(dateRangeModal, openerEl || document.body);
    }

    function updateCustomRangeInfo(startISO, endISO, show){
        const info = document.getElementById('custom-range-info');
        const setVis = (el, on) => { if (el) el.style.display = on ? '' : 'none'; };
        if (!show){
            setVis(info, false);
            return;
        }
        if (!startISO || !endISO){
            setVis(info, false);
            return;
        }
        const s = startISO <= endISO ? startISO : endISO;
        const e = endISO >= startISO ? endISO : startISO;
        const d1 = new Date(s + 'T00:00:00');
        const d2 = new Date(e + 'T00:00:00');
        const msPerDay = 24*3600*1000;
        const days = Math.floor((d2 - d1)/msPerDay) + 1;
        const text = `${s} to ${e} — ${days} day${days===1?'':'s'}`;
        if (info) info.textContent = text;
        setVis(info, true);
    }

    function buildCustomTables(startISO, endISO){
        const root = getDailyRoot();
        if (!root || !root.daily){
            alert('Custom date range is unavailable because per-day data is missing.');
            return false;
        }
        if (!startISO || !endISO){
            alert('Please select both start and end dates.');
            return false;
        }
        const s = startISO <= endISO ? startISO : endISO;
        const e = endISO >= startISO ? endISO : startISO;
        const names = root.names || [];
        const sumMap = {
            artist: new Map(),
            track: new Map(),
            album: new Map()
        };
        const pushRow = (kind, idx, pt, pc) => {
            const prev = sumMap[kind].get(idx) || [0,0];
            sumMap[kind].set(idx, [prev[0]+(pt||0), prev[1]+(pc||0)]);
        };
        const dates = Object.keys(root.daily).sort();
        for (const d of dates){
            if (d < s || d > e) continue;
            const day = root.daily[d];
            if (!day) continue;
            ["artist","track","album"].forEach(kind => {
                const rows = day[kind] || [];
                for (let i=0;i<rows.length;i++){
                    const r = rows[i];
                    const idx = r[0];
                    const pt = r[1]||0;
                    const pc = r[2]||0;
                    pushRow(kind, idx, pt, pc);
                }
            });
        }
        root.tables = root.tables || {};
        root.tables['artist-table-custom'] = Array.from(sumMap.artist.entries()).map(([idx,[pt,pc]])=>[idx,pt,pc]);
        root.tables['track-table-custom'] = Array.from(sumMap.track.entries()).map(([idx,[pt,pc]])=>[idx,pt,pc]);
        root.tables['album-table-custom'] = Array.from(sumMap.album.entries()).map(([idx,[pt,pc]])=>[idx,pt,pc]);
        // Persist last used
        localStorage.setItem('customRange', JSON.stringify({start: s, end: e}));
        return true;
    }

    if (applyDateBtn){
        applyDateBtn.addEventListener('click', () => {
            const startVal = startInput.value;
            const endVal = endInput.value;
            if (!buildCustomTables(startVal, endVal)) return;

            // Ensure custom section exists and render
            ensureYearSection('custom');
            // Activate custom tab/section
            const customTab = document.querySelector('.year-tab[data-year="custom"]');
            if (customTab) activateTab(customTab);
            // Re-render custom tables
            ['artist-table','track-table','album-table'].forEach(base => {
                paginateTable(`${base}-custom`, itemsPerPage);
            });
            // Update info banners
            updateCustomRangeInfo(startVal, endVal, true);
            closeModal(dateRangeModal);
        });
    }
    if (cancelDateBtn){
        cancelDateBtn.addEventListener('click', () => {
            closeModal(dateRangeModal);
            // Ensure dropdown mirrors the active tab if it still shows custom
            if (yearSelect && yearSelect.value === 'custom'){
                const activeTab = document.querySelector('.year-tab.active');
                if (activeTab) yearSelect.value = activeTab.dataset.year;
            }
        });
    }

    // Close modals with Escape key
    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeModal(settingsModal);
            closeModal(everyYearModal);
        }
    });

    // — Initialize the input with saved or default value —
    const ippInput = document.getElementById("items-per-page-input");
    ippInput.value = itemsPerPage;

    document.getElementById("apply-settings").addEventListener("click", () => {
        const v = parseInt(ippInput.value, 10);
        if (!isNaN(v) && v > 0) {
            itemsPerPage = v;
            localStorage.setItem("itemsPerPage", v);
            // re‑paginate every table with the new page size
            document.querySelectorAll('.year-section').forEach(sec => {
                const yr = sec.id.split('-')[1];
                ['artist-table', 'track-table', 'album-table'].forEach(base =>
                    paginateTable(`${base}-${yr}`, itemsPerPage)
                );
            });
            // close the modal
            document.getElementById("settings-modal").style.display = "none";
        } else {
            alert("Please enter a positive integer for Items per page.");
        }
    });

    // year-tab click handler
    const yearTabs = document.querySelectorAll('.year-tab');
    const yearSelect = document.getElementById('year-select');
    // Track the last non-custom year so the dropdown never stays on "custom"
    let lastNonCustomYear = 'all';

    // Helper: build a compact label for the current custom range
    function buildCustomRangeLabel(startISO, endISO){
        if (!startISO || !endISO) return null;
        const s = startISO <= endISO ? startISO : endISO;
        const e = endISO >= startISO ? endISO : startISO;
        return `${s} to ${e}`;
        }

    // Helper: ensure a dedicated option that reflects the selected custom range exists
    function ensureCustomRangeOption(label){
        if (!yearSelect) return null;
        const val = 'custom-range';
        let opt = yearSelect.querySelector(`option[value="${val}"]`);
        if (!label){
            return opt;
        }
        if (!opt){
            opt = document.createElement('option');
            opt.value = val;
            const customStatic = yearSelect.querySelector('option[value="custom"]');
            if (customStatic && customStatic.nextSibling){
                yearSelect.insertBefore(opt, customStatic.nextSibling);
            } else if (customStatic){
                yearSelect.appendChild(opt);
            } else {
                yearSelect.appendChild(opt);
            }
        }
        opt.textContent = label;
        return opt;
    }

    // Function to activate a tab
    function activateTab(tab) {
        yearTabs.forEach(t => {
            t.classList.remove('active');
            t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');

        document.querySelectorAll('.year-section').forEach(sec => {
            sec.style.display = 'none';
            sec.setAttribute('aria-hidden', 'true');
        });
        const y = tab.dataset.year;
        const section = document.getElementById(`year-${y}`);
        // Ensure lazy section has its skeleton before showing and paginating
        ensureYearSection(y);
        section.style.display = 'block';
        section.setAttribute('aria-hidden', 'false');

        // Update/show custom range info when appropriate
        if (y === 'custom'){
            const saved = JSON.parse(localStorage.getItem('customRange')||'{}');
            updateCustomRangeInfo(saved.start, saved.end, !!(saved.start && saved.end));
        } else {
            updateCustomRangeInfo(null, null, false);
        }

        // Update last non-custom year and sync dropdown if present
        if (y !== 'custom') {
            lastNonCustomYear = y;
        }
        if (yearSelect) {
            // If switching to the custom section and a range exists, select the dynamic range option; otherwise fallback
            let targetVal = y;
            if (y === 'custom'){
                const saved = JSON.parse(localStorage.getItem('customRange')||'{}');
                const label = buildCustomRangeLabel(saved.start, saved.end);
                if (label){
                    ensureCustomRangeOption(label);
                    targetVal = 'custom-range';
                } else {
                    targetVal = lastNonCustomYear;
                }
            }
            if (yearSelect.value !== targetVal) {
                yearSelect.value = targetVal;
            }
        }

        // Ensure tables in this section are initialized/rendered for current mode
        ['artist-table','track-table','album-table'].forEach(base => {
            paginateTable(`${base}-${y}`, itemsPerPage);
        });

        // restore any saved searches in this section
        section.querySelectorAll('.search-input').forEach(input => {
            // map "artist-table-2023-search" → "artist-table-2023" → prefix "artist-table"
            const tableId = input.id.replace(/-search$/, '');
            const prefix = tableId.replace(/-(?:\d{4}|all|custom)$/, '');
            const term = searchTerms[prefix] || "";
            input.value = term;

            input.dispatchEvent(new Event('input'));
        });
    }

    // Set up tabs for accessibility
    const tabsContainer = document.getElementById('year-tabs');
    tabsContainer.setAttribute('role', 'tablist');
    tabsContainer.setAttribute('aria-label', 'Year selection');

    // Set up sections for accessibility
    document.querySelectorAll('.year-section').forEach(section => {
        section.setAttribute('role', 'tabpanel');
        section.setAttribute('aria-hidden', section.style.display === 'none' ? 'true' : 'false');
    });

    // Add click handler to each tab
    yearTabs.forEach(tab => {
        // Make tabs keyboard focusable
        tab.setAttribute('tabindex', '0');
        tab.setAttribute('role', 'tab');
        tab.setAttribute('aria-selected', tab.classList.contains('active') ? 'true' : 'false');

        // Set aria-controls attribute
        const year = tab.dataset.year;
        tab.setAttribute('aria-controls', `year-${year}`);

        // Click handler
        tab.addEventListener('click', () => {
            if (tab.dataset.year === 'custom') {
                openDateRangeModal(tab);
            } else {
                activateTab(tab);
            }
        });

        // Keyboard handler - activate on Enter or Space
        tab.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                if (tab.dataset.year === 'custom') {
                    openDateRangeModal(tab);
                } else {
                    activateTab(tab);
                }
            }
        });
    });

    // Add arrow key navigation for tabs
    tabsContainer.addEventListener('keydown', (e) => {
        if (e.target.classList.contains('year-tab')) {
            const currentTab = e.target;
            const tabsArray = Array.from(yearTabs);
            const currentIndex = tabsArray.indexOf(currentTab);

            // Right arrow or Down arrow - move to next tab
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                e.preventDefault();
                const nextIndex = (currentIndex + 1) % tabsArray.length;
                tabsArray[nextIndex].focus();
            }
            // Left arrow or Up arrow - move to previous tab
            else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                e.preventDefault();
                const prevIndex = (currentIndex - 1 + tabsArray.length) % tabsArray.length;
                tabsArray[prevIndex].focus();
            }
        }
    });

    // Wire up year dropdown (mobile)
    if (yearSelect) {
        // initialize value from active tab, and set lastNonCustomYear
        const activeTab = document.querySelector('.year-tab.active');
        if (activeTab) {
            const initY = activeTab.dataset.year;
            if (initY !== 'custom') {
                lastNonCustomYear = initY;
                yearSelect.value = initY;
            } else {
                // If custom is active on load and we have a saved range, show it; else fallback
                const saved = JSON.parse(localStorage.getItem('customRange')||'{}');
                const label = buildCustomRangeLabel(saved.start, saved.end);
                if (label){
                    ensureCustomRangeOption(label);
                    yearSelect.value = 'custom-range';
                } else {
                    yearSelect.value = lastNonCustomYear;
                }
            }
        }

        yearSelect.addEventListener('change', () => {
            const val = yearSelect.value;
            if (val === 'custom') {
                // Open modal but keep the current active tab showing; reset the dropdown
                // back to the last non-custom year so the user can select Custom again later.
                openDateRangeModal(yearSelect);
                // If a custom range option exists, prefer leaving that selected; otherwise fallback
                const exists = yearSelect.querySelector('option[value="custom-range"]');
                yearSelect.value = exists ? 'custom-range' : lastNonCustomYear;
            } else if (val === 'custom-range') {
                const targetTab = document.querySelector(`.year-tab[data-year="custom"]`);
                if (targetTab) activateTab(targetTab);
            } else {
                const targetTab = document.querySelector(`.year-tab[data-year="${val}"]`);
                if (targetTab) activateTab(targetTab);
                // hide custom info when switching away via dropdown
                updateCustomRangeInfo(null, null, false);
            }
        });
    }

    // Initialize tooltips for info buttons
    tippy('.info-button', {
        content: (reference) => reference.getAttribute('data-info'),
        allowHTML: true,
        placement: 'top',
        arrow: true,
        theme: 'spotify',
        maxWidth: '50em',
        trigger: 'click',
    });

    // Add touch event support for modal closing
    window.addEventListener('touchstart', e => {
        if (e.target.classList.contains('modal-overlay')) {
            closeModal(e.target);
        }
    });

    // Initialize tooltips for personality types
    tippy('.personality-bar-container', {
        allowHTML: true,
        placement: 'top',
        arrow: true,
        theme: 'spotify',
        maxWidth: '50em'
    });
});
