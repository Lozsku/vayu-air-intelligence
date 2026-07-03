// Vayu dashboard client.
const $ = (id) => document.getElementById(id);
const AQI_COLORS = [
  [50, '#2ecc71'], [100, '#f1c40f'], [150, '#e67e22'],
  [200, '#e74c3c'], [300, '#8e44ad'], [500, '#7e0023'],
];
function aqiColor(a) {
  if (a == null) return '#334';
  for (const [hi, c] of AQI_COLORS) if (a <= hi) return c;
  return '#7e0023';
}

const state = { city: null, station: null, dominant: 'pm25', profile: 'general' };

const SAMPLES = [
  'Is it safe for my kid to play outside in Delhi this evening?',
  'Should I go for a run in Bangkok tomorrow morning?',
  'How is the air trending in Jakarta this week?',
  'Which city has the worst air right now?',
];

async function api(path, opts) {
  const r = await fetch('/api' + path, opts);
  return r.json();
}

// ---------------- init ----------------
async function init() {
  const meta = await api('/meta');
  $('aiBadge').textContent = 'AI: ' + meta.ai_backend;
  $('liveBadge').textContent = 'Data: ' + (meta.live_data ? 'live + bundled' : 'bundled');
  if (window.__REPO_URL__) $('repoBadge').href = window.__REPO_URL__;

  SAMPLES.forEach(s => {
    const c = document.createElement('span');
    c.className = 'chip'; c.textContent = s;
    c.onclick = () => { $('askInput').value = s; doAsk(); };
    $('sampleChips').appendChild(c);
  });

  $('askBtn').onclick = doAsk;
  $('askInput').addEventListener('keydown', e => { if (e.key === 'Enter') doAsk(); });
  $('profileSelect').onchange = () => { state.profile = $('profileSelect').value; loadDecision(); };

  await loadCities();
  await loadAlerts();
  if (state.city) selectCity(state.city);
}

// ---------------- cities ----------------
async function loadCities() {
  const cities = await api('/cities');
  const list = $('cityList');
  list.innerHTML = '';
  cities.forEach((c, i) => {
    if (i === 0) state.city = c.city;
    const el = document.createElement('div');
    el.className = 'city-item';
    el.dataset.city = c.city;
    el.innerHTML = `
      <div class="city-name">${c.city}<small>${c.country} · ${c.stations} stations</small></div>
      <div class="aqi-pill" style="background:${aqiColor(c.aqi)}">${c.aqi ?? '—'}</div>`;
    el.onclick = () => selectCity(c.city);
    list.appendChild(el);
  });
}

async function selectCity(city) {
  state.city = city;
  document.querySelectorAll('.city-item').forEach(e =>
    e.classList.toggle('active', e.dataset.city === city));
  const snap = await api('/city/' + encodeURIComponent(city));
  if (!snap.stations || !snap.stations.length) return;
  const worst = snap.stations.reduce((a, b) => (b.aqi.aqi > a.aqi.aqi ? b : a));
  state.station = worst.station.id;
  state.dominant = worst.aqi.dominant || 'pm25';
  renderDetail(city, worst);
  await Promise.all([loadTrend(), loadDecision(), loadEpisodes()]);
}

function renderDetail(city, s) {
  $('detailCity').textContent = city;
  $('detailStation').textContent = 'Worst station: ' + s.station.name + ' · updated ' +
    (s.updated ? new Date(s.updated).toLocaleString() : '—');
  const a = s.aqi;
  $('gaugeVal').textContent = a.aqi;
  $('gaugeCat').textContent = a.category;
  $('gauge').style.borderColor = a.color;
  $('gaugeVal').style.color = a.color;

  const pol = $('pollutants');
  pol.innerHTML = '';
  Object.entries(s.readings).forEach(([k, v]) => {
    const d = document.createElement('div');
    d.className = 'pollutant';
    d.innerHTML = `<div class="p-val">${v.value}</div><div class="p-lab">${v.label} · µg/m³</div>`;
    pol.appendChild(d);
  });
}

async function loadTrend() {
  const [hist, fc] = await Promise.all([
    api(`/station/${state.station}/series?pollutant=${state.dominant}&hours=168`),
    api(`/station/${state.station}/forecast?pollutant=${state.dominant}`),
  ]);
  $('forecastMeta').textContent = `· ${fc.method} · trend ${fc.trend}`;
  renderTrend(hist, fc);
}

async function loadDecision() {
  if (!state.station) return;
  const d = await api(`/station/${state.station}/decision?profile=${state.profile}`);
  const box = $('decisionBox');
  box.classList.remove('hidden');
  $('decisionIcon').textContent = d.safe_outdoors ? '✅' : '⚠️';
  $('decisionTitle').textContent = d.safe_outdoors
    ? 'Outdoor activity is OK right now'
    : 'Limit outdoor activity';
  $('decisionText').textContent =
    `${d.guidance} Forecast peak ${d.forecast_peak.aqi} AQI (${d.forecast_peak.category}) ` +
    `around ${d.forecast_peak.at ? new Date(d.forecast_peak.at).toLocaleString([], {hour:'2-digit', minute:'2-digit', weekday:'short'}) : 'later'}.`;
  $('profileSelect').value = state.profile;
}

async function loadEpisodes() {
  const anos = await api(`/station/${state.station}/anomalies?pollutant=${state.dominant}`);
  const box = $('episodes');
  box.innerHTML = '';
  if (!anos.length) return;
  const h = document.createElement('div');
  h.innerHTML = `<h3 style="font-size:.9rem;margin-bottom:4px">Detected pollution episodes (7d)</h3>`;
  box.appendChild(h);
  anos.slice(-4).reverse().forEach(a => {
    const d = document.createElement('div');
    d.className = 'episode';
    d.innerHTML = `<b>${a.label} spike</b> — ${a.value} µg/m³ vs ${a.baseline} baseline ` +
      `(z=${a.z}) · ${new Date(a.ts * 1000).toLocaleString()}`;
    box.appendChild(d);
  });
}

// ---------------- alerts ----------------
async function loadAlerts() {
  const feed = await api('/alerts');
  const box = $('alertsFeed');
  box.innerHTML = '';
  if (!feed.length) { box.innerHTML = '<p class="muted small">No active alerts.</p>'; return; }
  feed.forEach(a => {
    const d = document.createElement('div');
    if (a.type === 'unhealthy') {
      d.className = 'alert unhealthy';
      d.innerHTML = `<b>${a.city}</b> — ${a.category} (AQI ${a.aqi}) at ${a.station}`;
    } else {
      d.className = 'alert';
      d.innerHTML = `<b>${a.city}</b> — ${a.pollutant} spike ${a.value} (base ${a.baseline}) · ${a.station}`;
    }
    box.appendChild(d);
  });
}

// ---------------- ask ----------------
async function doAsk() {
  const q = $('askInput').value.trim();
  if (!q) return;
  $('askBtn').disabled = true; $('askBtn').textContent = '…';
  try {
    const res = await api('/ask', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q, city: state.city }),
    });
    $('answerBox').classList.remove('hidden');
    $('answerText').textContent = res.answer;
    $('answerBackend').textContent = 'via ' + (res.backend || 'local') + ' AI';
    if (res.decision) {
      $('answerVerdict').textContent = res.decision.safe_outdoors ? '✅ Safe' : '⚠️ Take care';
      $('answerVerdict').style.color = res.decision.safe_outdoors ? '#2ecc71' : '#e67e22';
    } else { $('answerVerdict').textContent = ''; }
    $('answerGrounding').textContent = res.grounded_on || '—';
    if (res.city && res.city !== state.city) selectCity(res.city);
  } finally {
    $('askBtn').disabled = false; $('askBtn').textContent = 'Ask';
  }
}

init();
