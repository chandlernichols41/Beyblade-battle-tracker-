/* ============================================================
   Beyblade X Tracker — app.js
   Handles:
     - Combos page: toggle add form, row navigation
     - Battle page: winner select filter, points preview
     - Stats page: fetch + render stats, part filter
     - Parts page: search filter, category filter, modal
   ============================================================ */

'use strict';

// ============================================================
// Utility
// ============================================================
function $(selector, ctx) {
  return (ctx || document).querySelector(selector);
}

function $$(selector, ctx) {
  return Array.from((ctx || document).querySelectorAll(selector));
}

function onPage(path) {
  return window.location.pathname === path ||
         window.location.pathname.startsWith(path + '?');
}

// ============================================================
// COMBOS PAGE
// ============================================================
function initCombosPage() {
  const toggleBtn = $('#toggleAddForm');
  const cancelBtn = $('#cancelAddForm');
  const panel     = $('#addComboPanel');

  if (!toggleBtn || !panel) return;

  toggleBtn.addEventListener('click', function () {
    const isHidden = panel.style.display === 'none';
    panel.style.display = isHidden ? 'block' : 'none';
    toggleBtn.textContent = isHidden ? '− Hide Form' : '+ Add Combo';
    if (isHidden) {
      const firstInput = panel.querySelector('input');
      if (firstInput) firstInput.focus();
    }
  });

  if (cancelBtn) {
    cancelBtn.addEventListener('click', function () {
      panel.style.display = 'none';
      toggleBtn.textContent = '+ Add Combo';
    });
  }

  // Row click → navigate to stats
  $$('.combo-row').forEach(function (row) {
    row.addEventListener('click', function () {
      const comboName = row.dataset.combo;
      if (comboName) {
        // Store in localStorage so stats page can auto-load
        try { localStorage.setItem('bx_selected_combo', comboName); } catch(e) {}
        window.location.href = '/stats?combo=' + encodeURIComponent(comboName);
      }
    });
  });
}

// ============================================================
// BATTLE PAGE
// ============================================================
function initBattlePage() {
  var bey1Input    = $('#bey1Input');
  var bey2Input    = $('#bey2Input');
  var winnerSelect = $('#winnerSelect');
  var winTypeSelect = $('#winTypeSelect');
  var pointsPreview = $('#pointsPreview');
  var pointsValue   = $('#pointsValue');

  if (!bey1Input || !bey2Input || !winnerSelect) return;

  function updateWinnerOptions() {
    var n1 = bey1Input.value.trim();
    var n2 = bey2Input.value.trim();
    winnerSelect.innerHTML = '<option value="">— Select Winner —</option>';
    if (n1) {
      var opt1 = document.createElement('option');
      opt1.value = n1;
      opt1.textContent = n1;
      winnerSelect.appendChild(opt1);
    }
    if (n2 && n2 !== n1) {
      var opt2 = document.createElement('option');
      opt2.value = n2;
      opt2.textContent = n2;
      winnerSelect.appendChild(opt2);
    }
  }

  bey1Input.addEventListener('input', updateWinnerOptions);
  bey2Input.addEventListener('input', updateWinnerOptions);
  // Also catch datalist selection (fires as 'change' on some browsers)
  bey1Input.addEventListener('change', updateWinnerOptions);
  bey2Input.addEventListener('change', updateWinnerOptions);

  if (winTypeSelect && pointsPreview && pointsValue) {
    winTypeSelect.addEventListener('change', function () {
      var selected = winTypeSelect.options[winTypeSelect.selectedIndex];
      var pts = selected ? selected.dataset.pts : null;
      if (pts !== null && pts !== undefined && winTypeSelect.value) {
        pointsPreview.style.display = 'flex';
        pointsValue.textContent = pts;
      } else {
        pointsPreview.style.display = 'none';
      }
    });
  }
}

// ============================================================
// STATS PAGE
// ============================================================
var WIN_TYPE_LABELS = [
  'Spin/Stamina Finish',
  'Over Finish',
  'Burst Finish',
  'Extreme Finish',
];

var WIN_TYPE_PTS = {
  'Spin/Stamina Finish': 1,
  'Over Finish': 2,
  'Burst Finish': 2,
  'Extreme Finish': 3,
};

function initStatsPage() {
  var comboSelect   = $('#comboSelect');
  var showStatsBtn  = $('#showStatsBtn');
  var filterCard    = $('#partFilterCard');
  var partNameGroup = $('#partNameGroup');
  var partNameSelect = $('#partNameSelect');
  var statsArea     = $('#stats-area');

  if (!comboSelect) return;

  // Auto-load if combo passed via URL or localStorage
  var initialCombo = window.SELECTED_COMBO || '';
  if (!initialCombo) {
    try { initialCombo = localStorage.getItem('bx_selected_combo') || ''; } catch(e) {}
  }
  if (initialCombo) {
    comboSelect.value = initialCombo;
    try { localStorage.removeItem('bx_selected_combo'); } catch(e) {}
  }

  // Part type radio change → populate part name select
  $$('input[name="partType"]').forEach(function (radio) {
    radio.addEventListener('change', function () {
      updatePartNameSelect(radio.value);
      if (comboSelect.value && radio.value !== 'any') {
        // Re-fetch only if a part is selected
      }
    });
  });

  if (partNameSelect) {
    partNameSelect.addEventListener('change', function () {
      var combo = comboSelect.value;
      if (combo) fetchStats(combo);
    });
  }

  if (showStatsBtn) {
    showStatsBtn.addEventListener('click', function () {
      var combo = comboSelect.value;
      if (!combo) {
        statsArea.innerHTML = '<div class="empty-state"><p>Please select a combo first.</p></div>';
        return;
      }
      fetchStats(combo);
    });
  }

  // Auto-load on page init if combo is selected
  if (initialCombo && comboSelect.value) {
    setTimeout(function () { fetchStats(comboSelect.value); }, 50);
  }

  function getPartType() {
    var radio = $('input[name="partType"]:checked');
    return radio ? radio.value : 'any';
  }

  function getPartName() {
    return partNameSelect ? partNameSelect.value : '';
  }

  function updatePartNameSelect(partType) {
    if (!partNameSelect || !partNameGroup) return;
    if (partType === 'any') {
      partNameGroup.style.display = 'none';
      return;
    }
    partNameGroup.style.display = 'block';
    partNameSelect.innerHTML = '<option value="">— Select part —</option>';
    var names = [];
    if (partType === 'blade')   names = window.BLADE_NAMES   || [];
    if (partType === 'ratchet') names = window.RATCHET_NAMES || [];
    if (partType === 'bit')     names = window.BIT_NAMES     || [];
    names.forEach(function (n) {
      var opt = document.createElement('option');
      opt.value = n;
      opt.textContent = n;
      partNameSelect.appendChild(opt);
    });
  }

  function fetchStats(comboName) {
    if (!comboName) return;
    var partType = getPartType();
    var partName = getPartName();
    var url = '/api/stats/' + encodeURIComponent(comboName);
    if (partType !== 'any' && partName) {
      url += '?part_type=' + encodeURIComponent(partType) + '&part_name=' + encodeURIComponent(partName);
    }
    statsArea.innerHTML = '<div class="empty-state"><p>Loading...</p></div>';
    filterCard.style.display = 'block';

    fetch(url)
      .then(function (res) {
        if (!res.ok) throw new Error('Network error');
        return res.json();
      })
      .then(function (data) {
        if (data.error) {
          statsArea.innerHTML = '<div class="empty-state"><p>' + data.error + '</p></div>';
          return;
        }
        renderStats(data);
      })
      .catch(function (err) {
        statsArea.innerHTML = '<div class="empty-state"><p>Error loading stats. Try again.</p></div>';
        console.error(err);
      });
  }

  window.fetchStats = fetchStats;
}

function renderStats(data) {
  var statsArea = $('#stats-area');
  if (!statsArea) return;

  var partLine = [data.blade, data.ratchet, data.bit].filter(Boolean).join(' / ') || 'No parts set';
  var winPctColor = data.win_pct >= 60 ? '#4caf50' : (data.win_pct <= 40 ? '#e94560' : '#ffd700');

  var html = '';

  // Combo title
  html += '<div class="card" style="margin-bottom:14px;">';
  html += '<div class="stats-combo-title">' + escHtml(data.name) + '</div>';
  html += '<div class="stats-combo-parts">' + escHtml(partLine) + '</div>';

  // 6 stat cards
  html += '<div class="stat-cards-grid">';
  html += statCard(data.wins,              'Wins',           '#4caf50');
  html += statCard(data.losses,            'Losses',         '#e94560');
  html += statCard(data.win_pct + '%',     'Win Rate',       winPctColor);
  html += statCard(data.battles,           'Battles',        '#e0e0e0');
  html += statCard(data.pts,               'Pts Earned',     '#00bcd4');
  html += statCard(data.avg_pts_per_round, 'Avg Pts/Round',  '#8888aa');
  html += '</div>';
  html += '</div>';

  // Win Type Breakdown
  html += '<div class="section-title" style="margin-top:4px;">Win Type Breakdown</div>';
  html += '<div class="wt-grid" style="margin-bottom:16px;">';
  WIN_TYPE_LABELS.forEach(function (wt) {
    var count = (data.wt_counts && data.wt_counts[wt] !== undefined) ? data.wt_counts[wt] : 0;
    var pts   = WIN_TYPE_PTS[wt] || 0;
    html += '<div class="wt-card">';
    html += '<div class="wt-name">' + escHtml(wt) + '</div>';
    html += '<div class="wt-count">' + count + '</div>';
    html += '<div style="font-size:11px;color:#8888aa;">' + pts + ' pt' + (pts !== 1 ? 's' : '') + ' each</div>';
    html += '</div>';
  });
  html += '</div>';

  // Matchup Breakdown
  if (data.opponents && data.opponents.length > 0) {
    html += '<div class="section-title">Matchup Breakdown</div>';
    html += '<div class="table-wrapper" style="margin-bottom:16px;">';
    html += '<table class="data-table">';
    html += '<thead><tr>';
    html += '<th>Opponent</th><th class="text-center">W</th><th class="text-center">L</th>';
    html += '<th class="text-center">Battles</th><th class="text-center">Win%</th><th class="text-center">Pts</th>';
    html += '</tr></thead><tbody>';
    data.opponents.forEach(function (opp) {
      var oppWinPct = opp.win_pct;
      var oppClass  = oppWinPct >= 60 ? 'text-win' : (oppWinPct <= 40 ? 'text-loss' : '');
      html += '<tr>';
      html += '<td class="text-accent font-bold">' + escHtml(opp.name) + '</td>';
      html += '<td class="text-center text-win">' + opp.w + '</td>';
      html += '<td class="text-center text-loss">' + opp.l + '</td>';
      html += '<td class="text-center">' + opp.battles + '</td>';
      html += '<td class="text-center ' + oppClass + '">' + oppWinPct + '%</td>';
      html += '<td class="text-center text-gold">' + opp.pts + '</td>';
      html += '</tr>';
    });
    html += '</tbody></table></div>';
  }

  // Battle History
  if (data.history && data.history.length > 0) {
    html += '<div class="section-title">Battle History</div>';
    html += '<div class="table-wrapper">';
    html += '<table class="data-table">';
    html += '<thead><tr>';
    html += '<th>Date</th><th>Opponent</th><th class="text-center">Result</th>';
    html += '<th>Win Type</th><th class="text-center">Pts</th>';
    html += '</tr></thead><tbody>';
    data.history.forEach(function (h) {
      var rowClass = h.result === 'WIN' ? 'row-win' : 'row-loss';
      var resultColor = h.result === 'WIN' ? '#4caf50' : '#e94560';
      html += '<tr class="' + rowClass + '">';
      html += '<td class="text-muted text-sm">' + escHtml(h.date) + '</td>';
      html += '<td>' + escHtml(h.opp) + '</td>';
      html += '<td class="text-center font-bold" style="color:' + resultColor + ';">' + h.result + '</td>';
      html += '<td class="win-type-cell text-sm">' + escHtml(h.win_type) + '</td>';
      html += '<td class="text-center text-gold">' + h.pts + '</td>';
      html += '</tr>';
    });
    html += '</tbody></table></div>';
  }

  if (!data.battles) {
    html += '<div class="empty-state" style="margin-top:16px;"><p>No battles recorded for this combo yet.</p></div>';
  }

  statsArea.innerHTML = html;
}

function statCard(value, label, color) {
  return '<div class="stat-card">' +
    '<div class="stat-card-value" style="color:' + color + ';">' + value + '</div>' +
    '<div class="stat-card-label">' + escHtml(label) + '</div>' +
    '</div>';
}

function escHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ============================================================
// PARTS PAGE
// ============================================================
function initPartsPage() {
  var searchInput = $('#partsSearch');
  var grid        = $('#partsGrid');
  var modal       = $('#partModal');

  if (!grid) return;

  function filterParts() {
    var query = searchInput ? searchInput.value.toLowerCase().trim() : '';
    var catRadio = $('input[name="partsCat"]:checked');
    var cat = catRadio ? catRadio.value : 'all';

    $$('.part-card', grid).forEach(function (card) {
      var cardCat  = card.dataset.category || '';
      var cardName = card.dataset.name || '';

      var catMatch  = (cat === 'all') || (cardCat === cat);
      var nameMatch = !query || cardName.includes(query);

      card.classList.toggle('hidden', !(catMatch && nameMatch));
    });
  }

  if (searchInput) {
    searchInput.addEventListener('input', filterParts);
  }

  $$('input[name="partsCat"]').forEach(function (radio) {
    radio.addEventListener('change', filterParts);
  });

  // Modal
  window.selectPart = function (card) {
    if (!modal) return;
    $$('.part-card').forEach(function (c) { c.classList.remove('selected'); });
    card.classList.add('selected');

    var img     = card.querySelector('.part-img');
    var name    = card.querySelector('.part-name');
    var badge   = card.querySelector('.part-badge');
    var catKey  = card.dataset.category || '';

    var modalImg     = $('#modalImg');
    var modalPlaceholder = $('#modalPlaceholder');
    var modalName    = $('#modalName');
    var modalBadge   = $('#modalBadge');
    var placeholder  = card.querySelector('.part-img-placeholder');

    if (modalImg && modalPlaceholder) {
      if (img && img.src && !img.style.display) {
        modalImg.src = img.src;
        modalImg.alt = name ? name.textContent : '';
        modalImg.style.display = 'block';
        modalPlaceholder.style.display = 'none';
      } else {
        var icon = placeholder ? placeholder.textContent : '?';
        modalImg.style.display = 'none';
        modalPlaceholder.style.display = 'flex';
        modalPlaceholder.textContent = icon;
      }
    }

    if (modalName) modalName.textContent = name ? name.textContent : '';
    if (modalBadge && badge) {
      modalBadge.innerHTML = '';
      var newBadge = badge.cloneNode(true);
      modalBadge.appendChild(newBadge);
    }

    modal.style.display = 'flex';
  };

  window.closeModal = function (event) {
    if (modal && event.target === modal) {
      modal.style.display = 'none';
    }
  };

  // Close modal on Escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modal) {
      modal.style.display = 'none';
    }
  });
}

// ============================================================
// Init on DOM ready
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
  var path = window.location.pathname;

  if (path === '/combos' || path === '/combos/') {
    initCombosPage();
  }

  if (path === '/battle' || path === '/battle/') {
    initBattlePage();
  }

  if (path === '/stats' || path === '/stats/' || path.startsWith('/stats?')) {
    initStatsPage();
  }

  if (path === '/parts' || path === '/parts/') {
    initPartsPage();
  }
});
