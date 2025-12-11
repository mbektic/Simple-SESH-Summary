const themeStyle = document.getElementById("theme-style");
const currentTheme = localStorage.getItem("theme") || "dark";
themeStyle.textContent = currentTheme === "dark" ? DARK_CSS : LIGHT_CSS;
const originalRowCache = {};
const searchTerms = {};
let itemsPerPage = parseInt(localStorage.getItem("itemsPerPage"), 5) || 5;

window.onload = () => {
    const overlay = document.getElementById('loading-overlay');

    requestAnimationFrame(() => {
        document.querySelectorAll('.year-section').forEach(sec => {
            const yr = sec.id.split('-')[1];
            paginateTable(`artist-table-${yr}`, itemsPerPage);
            paginateTable(`track-table-${yr}`, itemsPerPage);
            paginateTable(`album-table-${yr}`, itemsPerPage);
        });

        // Trigger the fade-out
        overlay.classList.add('fade-out');

        // Re-enable scrolling after fade-out transition
        overlay.addEventListener('transitionend', () => {
            document.body.style.overflow = '';
            document.documentElement.style.overflow = '';
        }, {once: true});
    });
};

function paginateTable(tableId, pageSize) {
    const mode = document.querySelector(`#${tableId}-playcount`).style.display !== 'none' ? 'playcount' : 'playtime';
    const visibleTable = document.querySelector(`#${tableId}-${mode} table`);
    const tbody = visibleTable.querySelector("tbody");
    const searchInput = document.getElementById(`${tableId}-search`);
    const cacheKey = `${tableId}-${mode}`;

    if (!originalRowCache[cacheKey]) {
        originalRowCache[cacheKey] = Array.from(tbody.querySelectorAll("tr")).map(tr => tr.cloneNode(true));
    }

    const originalRows = originalRowCache[cacheKey];
    let filteredRows = [...originalRows];
    let currentPage = 1;

    function renderPage(page) {
        currentPage = page;
        const start = (page - 1) * pageSize;
        const end = page * pageSize;
        const frag = document.createDocumentFragment();

        filteredRows.slice(start, end).forEach(tr => {
            frag.appendChild(tr.cloneNode(true));
        });

        tbody.innerHTML = "";
        tbody.appendChild(frag);

        requestAnimationFrame(renderPagination);

        const term = searchInput.value;
        const prefix = tableId.replace(/-(?:\d{4}|all)$/, '');
        searchTerms[prefix] = term;       // save it
        highlightVisibleMatches(term);
    }

    function renderPagination() {
        const totalPages = Math.ceil(filteredRows.length / pageSize);
        const nav = document.getElementById(`${tableId}-nav`);
        nav.innerHTML = "";

        function createButton(label, page, active = false, disabled = false) {
            const btn = document.createElement("button");
            btn.textContent = label;
            if (active) btn.classList.add("active");
            if (disabled) btn.disabled = true;
            btn.onclick = () => renderPage(page);
            nav.appendChild(btn);
        }

        createButton("Prev", currentPage - 1, false, currentPage === 1);

        const pageWindow = 1;
        const startPage = Math.max(1, currentPage - pageWindow);
        const endPage = Math.min(totalPages, currentPage + pageWindow);

        if (startPage > 1) {
            createButton("1", 1);
            if (startPage > 2) nav.appendChild(document.createTextNode("..."));
        }

        for (let i = startPage; i <= endPage; i++) {
            createButton(i, i, i === currentPage);
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) nav.appendChild(document.createTextNode("..."));
            createButton(totalPages, totalPages);
        }

        createButton("Next", currentPage + 1, false, currentPage === totalPages);
    }

    function applySearch(term) {
        const lowerTerm = term.toLowerCase();

        filteredRows = originalRows.filter(tr =>
            tr.textContent.toLowerCase().includes(lowerTerm)
        );

        if (filteredRows.length === 0) {
            const colCount = originalRows[0]?.children.length || 1;
            const noResultsRow = document.createElement("tr");
            const td = document.createElement("td");
            td.style.height = "300px";
            td.colSpan = colCount;
            td.textContent = "No results found.";
            td.style.textAlign = "center";
            noResultsRow.appendChild(td);
            filteredRows = [noResultsRow];
        }

        renderPage(1);

        // Highlight matches only if there are results
        if (filteredRows.length > 0 && filteredRows[0].textContent !== "No results found.") {
            highlightVisibleMatches(term);
        }
    }

    function highlightVisibleMatches(term) {
        if (!term) return;

        const regex = new RegExp(`(${term})`, "gi");
        const tbody = document.querySelector(`#${tableId}-${mode} table tbody`);
        const rows = tbody.querySelectorAll("tr");

        rows.forEach(row => {
            row.querySelectorAll("td").forEach(cell => {
                const originalText = cell.textContent;
                cell.innerHTML = originalText.replace(regex, `<span class="highlight">$1</span>`);
            });
        });
    }

    if (searchInput) {
        // derive a “prefix” like "artist-table" or "track-table" (drops "-2023" or "-all")
        const prefix = tableId.replace(/-(?:\d{4}|all)$/, '');
        searchInput.addEventListener("input", () => {
            const term = searchInput.value;
            searchTerms[prefix] = term;       // save it
            applySearch(term);
        });
    }

    renderPage(currentPage);
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

        document.querySelectorAll('.year-section').forEach(sec => {
            const yr = sec.id.split('-')[1];          // e.g. "all", "2023", etc.
            ["artist-table", "track-table", "album-table"].forEach(base => {
                switchMode(`${base}-${yr}`, newMode);
            });
        });

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
    const playcountDiv = document.getElementById(`${tableId}-playcount`);
    const playtimeDiv = document.getElementById(`${tableId}-playtime`);

    if (mode === 'playcount') {
        playcountDiv.style.display = 'block';
        playtimeDiv.style.display = 'none';
    } else {
        playcountDiv.style.display = 'none';
        playtimeDiv.style.display = 'block';
    }

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
        section.style.display = 'block';
        section.setAttribute('aria-hidden', 'false');

        // sync dropdown if present
        if (yearSelect && yearSelect.value !== y) {
            yearSelect.value = y;
        }

        // restore any saved searches in this section
        section.querySelectorAll('.search-input').forEach(input => {
            // map "artist-table-2023-search" → "artist-table-2023" → prefix "artist-table"
            const tableId = input.id.replace(/-search$/, '');
            const prefix = tableId.replace(/-(?:\d{4}|all)$/, '');
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
            activateTab(tab);
        });

        // Keyboard handler - activate on Enter or Space
        tab.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                activateTab(tab);
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
        // initialize value from active tab
        const activeTab = document.querySelector('.year-tab.active');
        if (activeTab) {
            yearSelect.value = activeTab.dataset.year;
        }

        yearSelect.addEventListener('change', () => {
            const val = yearSelect.value;
            const targetTab = document.querySelector(`.year-tab[data-year="${val}"]`);
            if (targetTab) {
                activateTab(targetTab);
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
