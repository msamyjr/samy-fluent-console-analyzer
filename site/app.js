/* ES5 syntax and XHR for older TV engines. No libraries, tracking, or TV tokens. */
(function () {
  'use strict';
  var control = document.body.getAttribute('data-mode') === 'control';
  var apps = [], favorites = [], filter = 'all', csrf = '', offline = true, busy = false;
  var notice = document.getElementById('notice'), search = document.getElementById('search');
  var storageKey = 'samy-home-favorites-v1', storageAvailable = true;
  var remoteCounts = {}, remotePanel = document.getElementById('remote-panel');
  function showRemoteCounts(key) {
    var arrows = ['ArrowLeft', 'ArrowUp', 'ArrowRight', 'ArrowDown'], seen = 0, back;
    for (var i = 0; i < arrows.length; i++) if (remoteCounts[arrows[i]]) seen++;
    back = (remoteCounts.Escape || 0) + (remoteCounts.BrowserBack || 0) + (remoteCounts.GoBack || 0) + (remoteCounts.Backspace || 0);
    document.getElementById('remote-counts').textContent = 'Arrows: ' + seen + ' / 4 · OK: ' + (remoteCounts.Enter || 0) + ' · Back: ' + back;
    document.getElementById('remote-last').textContent = key ? 'Last browser navigation event: ' + key : 'No navigation events received in this test.';
  }
  document.getElementById('remote-check').addEventListener('click', function () { remotePanel.hidden = false; showRemoteCounts(); });
  document.getElementById('remote-close').addEventListener('click', function () { remotePanel.hidden = true; document.getElementById('remote-check').focus(); });
  document.getElementById('remote-reset').addEventListener('click', function () { remoteCounts = {}; showRemoteCounts(); });

  var noticeTimer = null;
  function tell(text, error) {
    clearTimeout(noticeTimer); notice.textContent = text; notice.className = 'notice' + (error ? ' error' : '');
    if (!error) noticeTimer = setTimeout(function () { notice.classList.add('quiet'); }, 5500);
  }
  function loadFavorites() {
    try { var value = JSON.parse(localStorage.getItem(storageKey) || '[]'); if (Object.prototype.toString.call(value) === '[object Array]') favorites = value.filter(function (v) { return typeof v === 'string'; }); }
    catch (e) { storageAvailable = false; }
  }
  function isFavorite(id) { return favorites.indexOf(id) !== -1; }
  function saveFavorite(id) {
    var i = favorites.indexOf(id);
    if (i === -1) favorites.push(id); else favorites.splice(i, 1);
    try { localStorage.setItem(storageKey, JSON.stringify(favorites)); } catch (e) { storageAvailable = false; }
    tell((i === -1 ? 'Added to your library.' : 'Removed from your library.') + (storageAvailable ? ' Saved locally in this browser.' : ' Storage is unavailable; changes last for this session only.'));
  }
  function request(path, body, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open(body === null ? 'GET' : 'POST', path, true);
    xhr.timeout = 30000;
    if (body !== null) { xhr.setRequestHeader('Content-Type', 'application/json'); xhr.setRequestHeader('X-Samy-CSRF', csrf); }
    xhr.onload = function () {
      var data;
      try { data = JSON.parse(xhr.responseText); } catch (e) { callback('The server returned an invalid response.'); return; }
      if (xhr.status < 200 || xhr.status >= 300 || data.ok === false) { callback('The operation failed. Check the TV connection and local setup; run diagnostics in Terminal.'); return; }
      callback(null, data);
    };
    xhr.onerror = function () { callback('Cannot reach the local server.'); };
    xhr.ontimeout = function () { callback('The request timed out. Check the connection.'); };
    xhr.send(body === null ? null : JSON.stringify(body));
  }
  function output(data) { var out = document.getElementById('result'); if (out) out.textContent = JSON.stringify(data, null, 2); }
  function command(path, body) {
    if (!control) { tell('Use the local Mac dashboard to launch native apps. The TV page is static and read-only.'); return; }
    if (offline) { tell('Offline preview. Run setup on your Mac, then restart the server.', true); return; }
    if (busy) { tell('Please wait for the previous command to finish.'); return; }
    busy = true; document.body.classList.add('busy'); tell('Sending command…');
    request(path, body, function (error, data) {
      busy = false; document.body.classList.remove('busy');
      if (error) { tell(error, true); return; }
      output(data); tell('The API accepted the command only. Verify the TV screen; for app launches, also read the current app.');
      if (path === '/api/app' && body.app === 'watchfree') checkWatchFree();
    });
  }
  function checkWatchFree() {
    read('/api/watchfree/status', function (data) {
      var status = document.getElementById('watchfree-status'), text;
      if (data.matches_legacy_id === true) text = 'The TV reports the legacy WatchFree ID as the current app. Check channels and audio yourself; this does not confirm WatchFree+ availability in Malaysia.';
      else if (data.matches_legacy_id === false) text = 'The current app does not match the legacy WatchFree ID. Startup may take time, or your TV may not support this ID. Check again and inspect the screen.';
      else text = 'The response did not identify the current app. Inspect the TV screen; playback is not verified.';
      status.textContent = text; tell(text, data.matches_legacy_id === false);
    });
  }
  function read(path, callback) {
    if (offline) { tell('No TV is connected in offline preview.', true); return; }
    tell('Reading TV state…');
    request(path, null, function (error, data) {
      if (error) { tell(error, true); return; }
      output(data); tell('API read completed. This does not verify the screen or video playback.');
      if (callback) callback(data.data);
    });
  }
  function element(tag, className, text) {
    var e = document.createElement(tag); if (className) e.className = className; if (text !== undefined) e.textContent = text; return e;
  }
  function launch(app) {
    if (app.type === 'native') { command('/api/app', {app: app.id}); return; }
    if (!/^https:\/\//.test(app.url)) { tell('This link is not allowed.', true); return; }
    window.location.href = app.url;
  }
  function render(focusId) {
    var host = document.getElementById('apps'), query = search.value.toLowerCase().replace(/^\s+|\s+$/g, '');
    host.textContent = ''; var shown = 0, groups = {};
    ['native', 'web'].forEach(function (kind) {
      var group = element('section', 'catalog-group'), title = element('h3', 'row-title', kind === 'native' ? 'Your TV apps' : 'Explore on the web');
      title.appendChild(element('small', '', kind === 'native' ? 'SMARTCAST' : 'WEB · Not installed apps'));
      var row = element('div', 'app-row'); group.appendChild(title); group.appendChild(row); groups[kind] = {section: group, row: row, count: 0};
    });
    apps.forEach(function (app) {
      if (query && (app.name + ' ' + app.description).toLowerCase().indexOf(query) === -1) return;
      if (filter === 'favorites' && !isFavorite(app.id)) return;
      if ((filter === 'native' || filter === 'web') && app.type !== filter) return;
      shown++;
      var card = element('article', 'app-card app-' + app.id);
      card.setAttribute('data-app-id', app.id);
      var button = element('button', 'app-launch'); button.type = 'button'; button.setAttribute('aria-label', app.name + ' — ' + app.description);
      var art = element('span', 'app-art', app.symbol), info = element('span', 'app-info');
      art.setAttribute('aria-hidden', 'true');
      info.appendChild(element('strong', 'app-title', app.name)); info.appendChild(element('span', 'app-caption', app.description));
      button.appendChild(art); button.appendChild(info); button.addEventListener('click', function () { launch(app); });
      var favorite = element('button', 'favorite' + (isFavorite(app.id) ? ' saved' : ''), isFavorite(app.id) ? '★' : '☆');
      favorite.type = 'button'; favorite.setAttribute('aria-label', 'Favorite ' + app.name); favorite.setAttribute('aria-pressed', isFavorite(app.id) ? 'true' : 'false');
      favorite.addEventListener('click', function () { saveFavorite(app.id); render(app.id); });
      card.appendChild(button); card.appendChild(favorite); groups[app.type].row.appendChild(card); groups[app.type].count++;
    });
    ['native', 'web'].forEach(function (kind) { if (groups[kind].count) host.appendChild(groups[kind].section); });
    document.getElementById('count').textContent = shown + ' apps / websites';
    document.getElementById('empty').hidden = shown !== 0;
    if (focusId) {
      var cards = host.querySelectorAll('.app-card'), found = false;
      for (var i = 0; i < cards.length; i++) if (cards[i].getAttribute('data-app-id') === focusId) { cards[i].querySelector('.favorite').focus(); found = true; break; }
      if (!found) document.querySelector('[data-filter="' + filter + '"]').focus();
    }
  }
  function setFilter(value) {
    filter = value;
    var buttons = document.querySelectorAll('[data-filter]');
    for (var i = 0; i < buttons.length; i++) { var active = buttons[i].getAttribute('data-filter') === filter; buttons[i].classList.toggle('active', active); buttons[i].setAttribute('aria-pressed', active ? 'true' : 'false'); }
    var tabs = document.querySelectorAll('[data-nav-filter]');
    for (var j = 0; j < tabs.length; j++) tabs[j].classList.toggle('active', tabs[j].getAttribute('data-nav-filter') === value);
    render();
  }
  function loadInputs() {
    read('/api/inputs', function (inputs) {
      var host = document.getElementById('inputs'); host.textContent = '';
      if (!inputs.length) host.textContent = 'The TV did not advertise enabled inputs in a supported format.';
      inputs.forEach(function (input) { var b = element('button', '', input.name); if (input.writable === false) { b.disabled = true; b.title = 'The TV did not explicitly advertise this input as enabled.'; }
        b.addEventListener('click', function () { command('/api/input', {input: input.id}); }); host.appendChild(b); });
    });
  }
  function loadSettings(group) {
    read('/api/settings/' + group, function (settings) {
      var host = document.getElementById('settings'); host.textContent = '';
      if (!settings.length) host.textContent = 'No supported settings were advertised. Use the TV menu.';
      settings.forEach(function (setting, i) {
        var row = element('div', 'setting-row'), label = element('label', '', setting.name), id = 'setting-' + group + '-' + i;
        row.appendChild(label);
        if (!setting.spec) { row.appendChild(element('small', '', String(setting.value) + ' · ' + (setting.note || 'Read-only'))); host.appendChild(row); return; }
        var input, spec = setting.spec;
        if (spec.kind === 'enum') {
          input = element('select'); spec.choices.forEach(function (choice) { var option = element('option', '', String(choice)); option.value = JSON.stringify(choice); if (choice === setting.value) option.selected = true; input.appendChild(option); });
        } else {
          input = element('input'); input.type = 'number'; input.min = spec.min; input.max = spec.max; input.step = spec.step; input.value = setting.value;
        }
        input.id = id; label.htmlFor = id; row.appendChild(input);
        var apply = element('button', 'button secondary', 'Apply');
        apply.addEventListener('click', function () {
          var value = spec.kind === 'enum' ? JSON.parse(input.value) : Number(input.value);
          if (spec.kind !== 'enum' && (input.value === '' || !isFinite(value) || Math.floor(value) !== value)) { tell('Enter a valid whole number.', true); return; }
          command('/api/setting', {group: group, name: setting.id, value: value});
        }); row.appendChild(apply); host.appendChild(row);
      });
    });
  }
  function clock() { var date = new Date(); document.getElementById('clock').textContent = ('0' + date.getHours()).slice(-2) + ':' + ('0' + date.getMinutes()).slice(-2); }
  function visibleFocusable() {
    return Array.prototype.slice.call(document.querySelectorAll('a[href],button,input,select,summary')).filter(function (e) { return !e.disabled && e.getClientRects().length && e.offsetWidth && e.offsetHeight; });
  }
  // Geometry-based navigation follows rendered layout on resize and in RTL.
  function moveFocus(key) {
    var all = visibleFocusable(), current = document.activeElement;
    if (!all.length) return;
    if (all.indexOf(current) === -1) { all[0].focus(); return; }
    var r = current.getBoundingClientRect(), x = (r.left + r.right) / 2, y = (r.top + r.bottom) / 2, best = null, score = Infinity;
    all.forEach(function (candidate) {
      if (candidate === current) return;
      var c = candidate.getBoundingClientRect(), dx = (c.left + c.right) / 2 - x, dy = (c.top + c.bottom) / 2 - y;
      var horizontal = key === 'ArrowLeft' || key === 'ArrowRight';
      var forward = key === 'ArrowRight' ? dx : key === 'ArrowLeft' ? -dx : key === 'ArrowDown' ? dy : -dy;
      if (forward < 8) return;
      var lateral = Math.abs(horizontal ? dy : dx), value = forward + lateral * 3;
      if (value < score) { best = candidate; score = value; }
    });
    if (best) { best.focus(); try { best.scrollIntoView({block: 'nearest', inline: 'nearest'}); } catch (e) { best.scrollIntoView(false); } }
  }
  document.addEventListener('keydown', function (event) {
    var legacy = {37: 'ArrowLeft', 38: 'ArrowUp', 39: 'ArrowRight', 40: 'ArrowDown', 13: 'Enter', 8: 'Backspace', 27: 'Escape', 461: 'BrowserBack', 10009: 'BrowserBack'};
    var key = event.key; if (!key || key === 'Unidentified') key = legacy[event.keyCode];
    if (key === 'Back') key = 'BrowserBack';
    if (key === 'Select' || key === 'OK') key = 'Enter';
    var current = document.activeElement;
    var editing = current && /^(INPUT|SELECT|TEXTAREA)$/.test(current.tagName);
    if (!remotePanel.hidden && !editing && /^(Arrow(Left|Right|Up|Down)|Enter|Escape|BrowserBack|GoBack|Backspace)$/.test(key)) {
      remoteCounts[key] = (remoteCounts[key] || 0) + 1;
      showRemoteCounts(key);
    }

    if (key === 'Escape' || key === 'BrowserBack' || key === 'GoBack' || (key === 'Backspace' && !editing)) {
      if (current && current.tagName === 'SELECT') return;
      event.preventDefault(); search.value = ''; setFilter('all'); document.querySelector('[data-filter="all"]').focus(); return;
    }
    if (editing && (key === 'ArrowLeft' || key === 'ArrowRight' || current.tagName === 'SELECT' || (current.type === 'number' && (key === 'ArrowUp' || key === 'ArrowDown')))) return;
    if (/^Arrow(Up|Down|Left|Right)$/.test(key)) { event.preventDefault(); moveFocus(key); }
    else if (key === 'Enter' && !editing && current && /^(BUTTON|A)$/.test(current.tagName)) { event.preventDefault(); if (!event.repeat) current.click(); }
    else if (!editing && (key === 'f' || key === 'F')) {
      var node = current; while (node && node !== document.body && !node.getAttribute('data-app-id')) node = node.parentNode;
      if (node && node.getAttribute && node.getAttribute('data-app-id')) { var id = node.getAttribute('data-app-id'); saveFavorite(id); render(id); }
    }
  });
  Array.prototype.forEach.call(document.querySelectorAll('[data-watchfree-launch]'), function (b) {
    b.addEventListener('click', function () { command('/api/app', {app: 'watchfree'}); });
  });
  Array.prototype.forEach.call(document.querySelectorAll('[data-nav-filter]'), function (b) {
    b.addEventListener('click', function () { setFilter(b.getAttribute('data-nav-filter')); document.getElementById('catalog').scrollIntoView(); });
  });
  loadFavorites(); clock(); setInterval(clock, 30000);
  search.addEventListener('input', function () { render(); });
  Array.prototype.forEach.call(document.querySelectorAll('[data-filter]'), function (b) { b.addEventListener('click', function () { setFilter(b.getAttribute('data-filter')); }); });
  document.getElementById('show-favorites').addEventListener('click', function () { setFilter('favorites'); document.getElementById('catalog').scrollIntoView(); document.querySelector('[data-filter="favorites"]').focus(); });
  request('/tv/catalog.json', null, function (error, data) {
    if (error || !data || Object.prototype.toString.call(data.apps) !== '[object Array]') { tell('Cannot load the catalog. Check the project files.', true); return; }
    apps = data.apps; render();
    if (!control && !window.location.hash && document.activeElement === document.body) document.getElementById('browse-apps').focus();
    tell(control ? 'Choose an app or command on the Mac dashboard. Native app compatibility still requires real-device testing.' : 'Arrows to navigate · OK to select · Launch native apps from the Mac dashboard.');
  });
  if (control) {
    request('/api/session', null, function (error, data) {
      if (error) { tell(error, true); return; }
      csrf = data.csrf; offline = data.offline;
      document.getElementById('connection').textContent = offline ? 'Offline preview · No real TV commands or device results.' : 'Local control session. Select Read TV status to check connectivity.';
    });
    document.getElementById('watchfree-check').addEventListener('click', checkWatchFree);
    document.getElementById('refresh').addEventListener('click', function () { read('/api/status', function (data) { document.getElementById('connection').textContent = JSON.stringify(data); }); });
    document.getElementById('conjure').addEventListener('click', function () { command('/api/conjure', {}); });
    document.getElementById('load-inputs').addEventListener('click', loadInputs);
    document.getElementById('check-reachability').addEventListener('click', function () {
      request('/api/diagnostics', null, function (error, data) {
        if (error) { tell(error, true); return; } output(data);
        var compatibility = document.getElementById('compatibility-status'), state = data.data;
        compatibility.textContent = 'Conjure API: ' + (state.conjure_api_status || 'not attempted') +
          '. TV asset requests observed: ' + ((state.tv_assets_requested || []).length) +
          '. Rendering: inspect TV. Remote navigation: use Remote check on the TV.';
        tell(data.data.tv_page_requested_at_utc ? 'A page request arrived from the configured TV address. This does not prove visible rendering; check the screen.' : 'No page request from the configured TV address was observed this session. Check TV-to-Mac reachability.');
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll('[data-key]'), function (b) { b.addEventListener('click', function () { command('/api/key', {key: b.getAttribute('data-key')}); }); });
    Array.prototype.forEach.call(document.querySelectorAll('[data-read]'), function (b) { b.addEventListener('click', function () { read('/api/read/' + b.getAttribute('data-read')); }); });
    Array.prototype.forEach.call(document.querySelectorAll('[data-settings]'), function (b) { b.addEventListener('click', function () { loadSettings(b.getAttribute('data-settings')); }); });
  }
}());
