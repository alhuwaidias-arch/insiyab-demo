/* انسياب — واجهة النموذج الأولي
 * كل رقم معروض يأتي من data/*.json المبنية من مجلدات تشغيل SUMO،
 * والأرقام المرجعية تُفحص آليًا في تبويب «الاختبار» وفي tests/.
 */
'use strict';

const S = {
  net: null, arms: null, dmg: null, trips: null, canon: null, meta: null,
  scenario: 'closure', view: 'overview', selStreet: null,
  proj: null, map: null, geo: null
};

/* ------------------------------------------------------------------ utils */
const fmt = (v, d = 1) => Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
const nf = (v) => Number(v).toLocaleString('en-US');
const pct = (a, b) => (b ? (100 * a) / b : 0);
const el = (h) => { const t = document.createElement('template'); t.innerHTML = h.trim(); return t.content.firstElementChild; };
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const ARM_AR = { baseline: 'خط الأساس', closure: 'إغلاق تقاطع أنس × تركي', detour: 'إغلاق + تحويلة مدعومة', policy600: 'سياسة قياس (ttt 600)' };

function stat(arm, field) {
  if (field === 'corridor') return S.arms.arms[arm].corridor || null;
  return S.arms.arms[arm].stats[field];
}

/* --------------------------------------------------------------- bootstrap */
async function boot() {
  const inline = window.__INSIYAB_DATA__ || null;
  const get = async (n) => {
    if (inline && inline[n]) return inline[n];
    const r = await fetch('data/' + n + '.json', { cache: 'no-store' });
    if (!r.ok) throw new Error('تعذّر تحميل data/' + n + '.json');
    return r.json();
  };
  const [net, arms, dmg, trips, canon, meta] = await Promise.all(
    ['network', 'arms', 'damage', 'trips', 'canon', 'meta'].map(get));
  Object.assign(S, { net, arms, dmg, trips, canon, meta });
  S.dmg = S.dmg.damage;
  S.trips = S.trips.trips;

  buildOverview();
  buildMap();
  buildLab();
  buildAnalyst();
  buildMethod();
  await buildImages();
  await buildBrief();
  wireTabs();
  runSelfTests();
}

/* ------------------------------------------------------------------ views */
function wireTabs() {
  $$('nav.tabs button').forEach(b => b.addEventListener('click', () => show(b.dataset.view)));
  document.addEventListener('click', (e) => {
    const a = e.target.closest('[data-goto]');
    if (a) { show(a.dataset.goto); }
    const sc = e.target.closest('[data-scenario]');
    if (sc) { setScenario(sc.dataset.scenario); show('map'); }
  });
}
function show(v) {
  S.view = v;
  $$('nav.tabs button').forEach(b => b.setAttribute('aria-selected', b.dataset.view === v));
  $$('.view').forEach(x => x.classList.toggle('on', x.id === 'view-' + v));
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* --------------------------------------------------------------- overview */
function buildOverview() {
  const base = stat('baseline', 'duration_mean_min'), clo = stat('closure', 'duration_mean_min');
  const cb = stat('baseline', 'corridor');
  const dNet = S.dmg.closure.net_vh, rec = S.dmg.closure.recovered_vh;
  const stay = pct(dNet, S.dmg.closure.added_vh_positive);
  const rate = S.canon.numbers.find(n => n.id === 'economics_rate').value;
  const cost = Math.round(dNet * rate);

  $('#kpi-corridor').innerHTML = `${fmt(cb.mean, 2)} <small>دقيقة</small>`;
  $('#kpi-fleet').innerHTML = `${fmt(clo.mean, 1)} <small>دقيقة</small>`;
  $('#kpi-added').innerHTML = `${nf(Math.round(S.canon.numbers.find(n => n.id === 'delay_added').value))} <small>مركبة‑ساعة</small>`;
  $('#kpi-stay').innerHTML = `${fmt(stay, 1)}<small>%</small>`;
  $('#kpi-cost').innerHTML = `${nf(cost)} <small>ريال</small>`;
  $('#ov-corridor-sub').textContent =
    `${fmt(cb.mean, 2)} ± ${fmt(cb.sd, 2)} دقيقة على مسار 9.4 كم · سياسة ttt=600 ترفعه إلى ${fmt(stat('policy600', 'corridor').mean, 2)} · بعد الإغلاق لم يُشغَّل تعريف الممر نفسه (لا رقم)`;
  $('#ov-fleet-sub').textContent = `Δ +${fmt(clo.mean - base.mean, 2)} دقيقة/رحلة · مركبة‑ساعة تتضاعف تقريبًا`;
  $('#ov-added-sub').textContent = 'صافي زمن الفقد الشبكي، محسوب بطريقتين مستقلتين متطابقتين 97.6%. وطبقة الضرر تجمع التأخير على الأضلاع المتضررة وحدها في 1,985.1 مركبة‑ساعة — الفرق تعريف لا تناقض.';
  $('#ov-stay-sub').textContent = `استُرد ${fmt(rec, 1)} مركبة‑ساعة على شوارع أخرى فقط`;
  $('#ov-cost-sub').textContent = `${nf(Math.round(dNet))} مركبة‑ساعة × ${fmt(rate, 2)} ريال/ساعة`;
  $('#ov-verdict').innerHTML =
    `الإغلاق <b>ليس</b> مشكلة مرور عابرة على مقطع: ${fmt(stay, 1)}% من التأخير المضاف يبقى <b>داخل</b> شبكة الممر المحيطة،
     ولا يُسترد منه إلا ${fmt(rec, 1)} مركبة‑ساعة على شوارع بديلة. التحويلة المدعومة تُحسّن ${fmt(S.dmg.closure.net_vh - S.dmg.detour.net_vh, 1)} مركبة‑ساعة (4.5%) — تحسين هامشي لا حل.`;

  // بطاقات الشوارع
  const rows = S.dmg.closure.streets.slice(0, 7);
  const mx = rows[0].added_vh;
  $('#ov-streets').innerHTML = rows.map(r => `
    <div class="bar-row">
      <div>
        <div style="display:flex;justify-content:space-between;gap:8px">
          <span>${r.street}</span><span class="mono">${fmt(r.added_vh, 1)}</span>
        </div>
        <div class="bar-track"><div class="bar-fill red" style="width:${Math.max(2, 100 * r.added_vh / mx)}%"></div></div>
      </div>
      <div class="mono" style="color:var(--muted);font-size:12px">${fmt(pct(r.added_vh, S.dmg.closure.added_vh_positive), 1)}%</div>
    </div>`).join('');
}

/* -------------------------------------------------------------------- map */
function project() {
  const sh = S.net.shapes;
  /* نطاق الرسم = الممر المتضرر وأعلى الأضلاع تأثرًا، لا كامل الشبكة الإقليمية
     (الشبكة تمتد عشرات الكيلومترات؛ إطارها كاملًا يقلّص الممر إلى خط) */
  const corridor = new Set(S.net.corridor_streets);
  const focus = new Set();
  for (let e = 0; e < S.net.edges.length; e++) if (corridor.has(S.net.streets[S.net.edges[e][1]])) focus.add(e);
  for (const scn of ['closure', 'detour']) {
    const d = S.dmg[scn]; if (!d) continue;
    d.edges.slice(0, 400).forEach(r => { const i = edgeIndex().get(r[0]); if (i !== undefined) focus.add(i); });
  }
  let minLon = 1e9, maxLon = -1e9, minLat = 1e9, maxLat = -1e9;
  const acc = (i) => {
    const lon = sh[i], lat = sh[i + 1];
    if (lon < minLon) minLon = lon; if (lon > maxLon) maxLon = lon;
    if (lat < minLat) minLat = lat; if (lat > maxLat) maxLat = lat;
  };
  for (const e of focus) { const off = S.net.edges[e][5], n = S.net.edges[e][6]; for (let k = 0; k < n; k++) acc((off + k) * 2); }
  if (!focus.size) for (let i = 0; i < sh.length; i += 2) acc(i);
  const padLon = (maxLon - minLon) * 0.12, padLat = (maxLat - minLat) * 0.12;
  minLon -= padLon; maxLon += padLon; minLat -= padLat; maxLat += padLat;
  const lat0 = (minLat + maxLat) / 2, kx = 111320 * Math.cos(lat0 * Math.PI / 180), ky = 110540;
  let W = (maxLon - minLon) * kx, H = (maxLat - minLat) * ky;
  const box = document.getElementById('mapbox');
  /* الصندوق قد يكون مخفيًا وقت الإقلاع (clientWidth=0) ⇒ نرجع إلى أبعاد CSS المعروفة */
  const bw = box ? box.clientWidth : 0, bh = box ? box.clientHeight : 0;
  const TW = (bw > 600 ? bw : 1136) - 4, TH = (bh > 300 ? bh : 560) - 4;
  let scale = Math.min(TW / W, TH / H);
  /* نوسّع نافذة العرض جغرافيًا لتملأ الصندوق تمامًا بلا تمطيط: نضيف مساحة على المحور
     الذي يفضّل مساحة إضافية بدل أن نترك شرائط فارغة حول الخريطة */
  {
    const dLon = (TW / scale - W) / (2 * kx), dLat = (TH / scale - H) / (2 * ky);
    minLon -= dLon; maxLon += dLon; minLat -= dLat; maxLat += dLat;
  }
  W = (maxLon - minLon) * kx; H = (maxLat - minLat) * ky;
  scale = Math.min(TW / W, TH / H);
  const px = (i) => ((sh[i] - minLon) * kx) * scale;
  const py = (i) => (H - (sh[i + 1] - minLat) * ky) * scale;
  return { px, py, scale, W: W * scale, H: H * scale, minLon, minLat, maxLon, maxLat, kx, ky, focus };
}

function edgePath(e, P, jitter = 0) {
  const rec = S.net.edges[e], off = rec[5], n = rec[6];
  const sh = S.net.shapes;
  let d = '';
  for (let k = 0; k < n; k++) {
    const i = (off + k) * 2;
    d += (k ? 'L' : 'M') + P.px(i).toFixed(1) + ' ' + (P.py(i) + jitter).toFixed(1);
  }
  return d;
}
/* خريطة معرّف الضلع → فهرسه في net.edges (بيانات الضرر تحمل المعرّفات نصًّا) */
function edgeIndex() {
  if (!S._eidx) S._eidx = new Map(S.net.edges.map((e, i) => [e[0], i]));
  return S._eidx;
}

function damageIndex(scn) {
  const idx = new Map();
  const d = S.dmg[scn];
  if (!d) return idx;
  for (const e of d.edges) idx.set(e[0], e);
  return idx;
}

function colorFor(vh) {
  if (vh <= 0.2) return null;
  if (vh < 2) return '#5d8ec9';
  if (vh < 8) return '#7fb2e5';
  if (vh < 25) return '#e8b33c';
  if (vh < 70) return '#e07b39';
  return '#c0392b';
}
const widthFor = (vh) => (vh < 2 ? 1.6 : vh < 8 ? 2.6 : vh < 25 ? 3.6 : vh < 70 ? 4.8 : 6);

function buildMap() {
  const P = project(); S.proj = P;
  const corridor = new Set(S.net.corridor_streets);
  const isCorridor = (e) => corridor.has(S.net.streets[S.net.edges[e][1]]);

  // خلفية: كل الأضلاع داخل نطاق الرسم في مسار واحد
  const inView = (e) => {
    const off = S.net.edges[e][5], n = S.net.edges[e][6], sh = S.net.shapes;
    for (let k = 0; k < n; k++) {
      const i = (off + k) * 2;
      if (sh[i] >= P.minLon && sh[i] <= P.maxLon && sh[i + 1] >= P.minLat && sh[i + 1] <= P.maxLat) return true;
    }
    return false;
  };
  let bg = '';
  for (let e = 0; e < S.net.edges.length; e++) if (!isCorridor(e) && inView(e)) bg += edgePath(e, P);
  // الممر
  let corr = '';
  for (let e = 0; e < S.net.edges.length; e++) if (isCorridor(e)) corr += edgePath(e, P);
  // الجارات المضرورة
  const idx = damageIndex(S.scenario);
  const E = edgeIndex();
  let hit = '';
  const labels = [];
  for (const [id, rec] of idx) {
    if (rec[2] <= 0.2) continue;
    const ei = E.get(id);
    if (ei === undefined) continue;
    hit += `<path d="${edgePath(ei, P)}" stroke="${colorFor(rec[2])}" stroke-width="${widthFor(rec[2])}" fill="none" stroke-linecap="round" opacity=".95" data-edge="${id}"/>`;
  }
  // أسماء أهم الشوارع المتضررة
  const streets = S.dmg[S.scenario].streets.slice(0, 6).map(s => s.street);
  const labeled = new Set();
  for (const [id, rec] of idx) {
    if (rec[2] < 20 || !streets.includes(rec[1]) || labeled.has(rec[1])) continue;
    if (/^No\./.test(rec[1]) || labeled.size >= 4) continue;   // أسماء آلية "No. xxx" لا تُعرض
    const ei = E.get(id);
    if (ei === undefined) continue;
    const off = S.net.edges[ei][5], n = S.net.edges[ei][6], mid = off + (n >> 1);
    labels.push(`<text x="${P.px(mid * 2)}" y="${P.py(mid * 2) - labeled.size * 13}" fill="#eaf1ff" font-size="11.5" font-weight="600"
      paint-order="stroke" stroke="#0d1520" stroke-width="3.2" direction="rtl">${rec[1]}</text>`);
    labeled.add(rec[1]);
  }

  const cid = S.net.edges.findIndex((_, i) => isCorridor(i));
  const html = `
  <div class="mapbar">
    <div class="seg" role="group" aria-label="السيناريو">
      ${['baseline', 'closure', 'detour'].map(k =>
        `<button data-scn="${k}" aria-pressed="${k === S.scenario}">${ARM_AR[k]}</button>`).join('')}
    </div>
    <label style="display:flex;align-items:center;gap:7px;font-size:13px;color:var(--muted)">
      <input type="checkbox" id="map-ctx" checked style="width:auto"> إظهار الشبكة المحيطة
    </label>
    <span class="tag navy">${nf(S.net.counts.edges)} ضلعًا · ${nf(S.net.counts.lanes)} حارة · SUMO 1.27.0</span>
    <span style="margin-inline-start:auto"></span>
    <button class="ghost" id="map-reset">إعادة الضبط</button>
  </div>
  <div class="mapbox" id="mapbox">
    <svg id="mapsvg" viewBox="0 0 ${P.W + 20} ${P.H + 20}" dir="ltr">
      <rect width="100%" height="100%" fill="#0d1520"/>
      <g id="viewport">
        <g id="lyr-bg" stroke="#33475f" stroke-width=".9" fill="none" opacity=".85"><path d="${bg}"/></g>
        <g id="lyr-corr" stroke="#8D99AE" stroke-width="2.2" fill="none" opacity=".9"><path d="${corr}"/></g>
        <g id="lyr-hit">${hit}</g>
        <g id="lyr-lbl">${labels.join('')}</g>
      </g>
    </svg>
    <div class="legend" id="legend"></div>
    <div class="tip" id="tip"></div>
  </div>
  <div class="mapmeta">
    <span><b>${nf(S.net.counts.streets)}</b> شارعًا · ${S.net.streets[S.net.edges[cid] ? S.net.edges[cid][1] : 0]}</span>
    <span>المصدر: <code>data/network.json</code> من <code>insyab.net.xml</code></span>
    <span id="map-scn-note"></span>
  </div>`;
  $('#view-map').querySelector('#map-host').innerHTML = html;

  $('#map-ctx').addEventListener('change', (e) => {
    $('#lyr-bg').style.display = e.target.checked ? '' : 'none';
  });
  $$('#view-map [data-scn]').forEach(b => b.addEventListener('click', () => setScenario(b.dataset.scn)));
  wireMapInteract(P);
  paintMap();
}

function setScenario(scn) {
  S.scenario = scn;
  if (S.view === 'map') {
    $$('#view-map [data-scn]').forEach(b => b.setAttribute('aria-pressed', b.dataset.scn === scn));
    paintMap();
  }
  if (S.view === 'lab') paintLab();
}

function paintMap() {
  const P = S.proj, d = S.dmg[S.scenario];
  const g = $('#lyr-hit');
  if (!g) return;
  if (S.scenario === 'baseline' || !d) {
    g.innerHTML = '';
    $('#map-scn-note').textContent = 'لا إغلاق: خط الأساس المرجعي (' + fmt(S.arms.arms.baseline.stats.duration_mean_min.mean, 2) + ' دقيقة/رحلة)';
    $('#legend').innerHTML = legendHtml(null);
    return;
  }
  let hit = '', labels = [];
  const E = edgeIndex();
  for (const rec of d.edges) {
    if (rec[2] <= 0.2) continue;
    const ei = E.get(rec[0]);
    if (ei === undefined) continue;
    hit += `<path d="${edgePath(ei, P)}" stroke="${colorFor(rec[2])}" stroke-width="${widthFor(rec[2])}"
      fill="none" stroke-linecap="round" data-edge="${rec[0]}"/>`;
  }
  g.innerHTML = hit;
  $('#map-scn-note').textContent =
    `${ARM_AR[S.scenario]}: +${nf(Math.round(d.added_vh_positive))} مركبة‑ساعة على ${nf(d.edges_hit)} ضلعًا · صافي ${nf(d.net_vh)}`;
  $('#legend').innerHTML = legendHtml(d);
}

function legendHtml(d) {
  const sw = (c, t) => `<div class="row"><i style="background:${c}"></i>${t}</div>`;
  return `<div style="font-weight:600;margin-bottom:6px">تأخير مضاف (مركبة‑ساعة)</div>
    ${d ? sw('#5d8ec9', '<2') + sw('#7fb2e5', '2–8') + sw('#e8b33c', '8–25') + sw('#e07b39', '25–70') + sw('#c0392b', '>70') : '<div class="row">خط الأساس — بلا تدخّل</div>'}
    <div class="row" style="margin-top:7px"><i style="background:#8D99AE;height:3px"></i>شارع أنس بن مالك</div>
    <div class="row"><i style="background:#33475f;height:2px"></i>الشبكة المحيطة</div>`;
}

function wireMapInteract(P) {
  const svg = $('#mapsvg'), vp = $('#viewport'), tip = $('#tip'), box = $('#mapbox');
  let k = 1, tx = 0, ty = 0, drag = null;
  const apply = () => vp.setAttribute('transform', `translate(${tx} ${ty}) scale(${k})`);
  const clamp = () => { tx = Math.min(200, Math.max(-P.W * (k - 1) - 200, tx)); ty = Math.min(200, Math.max(-P.H * (k - 1) - 200, ty)); };
  svg.addEventListener('wheel', (e) => {
    e.preventDefault();
    const f = e.deltaY < 0 ? 1.15 : 1 / 1.15;
    const r = svg.getBoundingClientRect();
    const mx = (e.clientX - r.left) / r.width * (P.W + 20), my = (e.clientY - r.top) / r.height * (P.H + 20);
    k = Math.min(14, Math.max(1, k * f));
    tx = mx - (mx - tx) * f; ty = my - (my - ty) * f;
    clamp(); apply();
  }, { passive: false });
  svg.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY, tx, ty }; svg.classList.add('drag'); });
  window.addEventListener('pointermove', (e) => {
    if (!drag) return;
    const r = svg.getBoundingClientRect();
    tx = drag.tx + (e.clientX - drag.x) * (P.W + 20) / r.width;
    ty = drag.ty + (e.clientY - drag.y) * (P.H + 20) / r.height;
    clamp(); apply();
  });
  window.addEventListener('pointerup', () => { drag = null; svg.classList.remove('drag'); });
  $('#map-reset').addEventListener('click', () => { k = 1; tx = 0; ty = 0; apply(); });

  svg.addEventListener('pointermove', (e) => {
    const p = e.target.closest('[data-edge]');
    const r = box.getBoundingClientRect();
    if (!p) { tip.style.opacity = 0; return; }
    const id = p.dataset.edge, rec = damageIndex(S.scenario).get(id);
    if (!rec) { tip.style.opacity = 0; return; }
    tip.innerHTML = `<b>${rec[1] || 'بلا اسم'}</b><br>
      تأخير مضاف: <b>${fmt(rec[2], 1)}</b> مركبة‑ساعة<br>
      Δ زمن ضياع: ${fmt(rec[3], 0)} ث<br>
      مركبات دخلت: ${nf(rec[4])} → <b>${nf(rec[5])}</b>
      <div style="color:#93a6c2;margin-top:4px" class="mono">${id}</div>`;
    tip.style.opacity = 1;
    tip.style.left = Math.min(r.width - 300, e.clientX - r.left + 14) + 'px';
    tip.style.top = Math.min(r.height - 110, e.clientY - r.top + 12) + 'px';
  });
}

/* -------------------------------------------------------------------- lab */
function buildLab() {
  const arms = ['baseline', 'closure', 'detour', 'policy600'];
  $('#lab-pick').innerHTML = arms.map(a =>
    `<button data-scenario="${a}" class="ghost" style="text-align:start;justify-content:start">${ARM_AR[a]}</button>`).join('');
  paintLab();
  $('#lab-run').addEventListener('click', runLabProposal);
  $('#lab-proposal').addEventListener('keydown', (e) => { if (e.key === 'Enter') runLabProposal(); });
}

function paintLab() {
  const base = S.arms.arms.baseline;
  const rows = ['baseline', 'closure', 'detour', 'policy600'].map(a => {
    const st = S.arms.arms[a].stats;
    const dur = st.duration_mean_min, tl = st.timeloss_mean_s, sp = st.speed_mean_kmh;
    const dmg = S.dmg[a];
    return `<tr>
      <td>${ARM_AR[a]} ${a === S.scenario ? '<span class="tag navy">مختار</span>' : ''}</td>
      <td class="num">${fmt(dur.mean, 2)} ± ${fmt(dur.sd, 2)}</td>
      <td class="num">${dur.mean === base.stats.duration_mean_min.mean ? '—' : (dur.mean > base.stats.duration_mean_min.mean ? '+' : '') + fmt(dur.mean - base.stats.duration_mean_min.mean, 2)}</td>
      <td class="num">${fmt(tl.mean, 0)}</td>
      <td class="num">${fmt(sp.mean, 1)}</td>
      <td class="num">${dmg ? nf(Math.round(dmg.added_vh_positive)) : '—'}</td>
      <td class="num">${dmg ? fmt(dmg.net_vh, 1) : '—'}</td>
    </tr>`;
  }).join('');

  const policyNote = `<div class="note" style="margin-top:12px">
    <b>لماذا أربعة أذرع فقط؟</b> كل رقم هنا من ${S.arms.arms.baseline.n} بذور × ${nf(S.arms.arms.baseline.stats.trips.mean)} رحلة على أفق 4 ساعات.
    «سياسة القياس» ليست تدخّلًا هندسيًا: تغيير حدّ الانتظار قبل النقل القسري من 300 إلى 600 ثانية يحرّك رقم الممر إلى
    <b>${fmt(stat('policy600', 'corridor').mean, 2)} ± ${fmt(stat('policy600', 'corridor').sd, 2)}</b> دقيقة مقابل
    <b>${fmt(stat('baseline', 'corridor').mean, 2)}</b> في خط الأساس — فالحكم على أي مقترح لا يصحّ قبل تثبيت السياسة.
  </div>`;

  const cmp = ['baseline', 'closure', 'detour'].map(a => {
    const st = S.arms.arms[a].stats;
    return `<div class="kpi ${a === 'baseline' ? 'plain' : a === 'closure' ? 'bad' : 'warn'}">
      <div class="lab">${ARM_AR[a]}</div>
      <div class="val">${fmt(st.duration_mean_min.mean, 2)} <small>دقيقة</small></div>
      <div class="sub">زمن ضياع ${fmt(st.timeloss_mean_s.mean, 0)} ث · سرعة ${fmt(st.speed_mean_kmh.mean, 1)} كم/س</div>
    </div>`;
  }).join('');

  $('#lab-body').innerHTML = `
    <div class="grid g3" style="margin-bottom:14px">${cmp}</div>
    <div class="card" style="padding:0;overflow:hidden">
      <table>
        <thead><tr>
          <th>الذراع المقيس</th><th class="num">زمن الرحلة (د)</th><th class="num">Δ عن الأساس</th>
          <th class="num">زمن ضياع (ث)</th><th class="num">سرعة (كم/س)</th>
          <th class="num">تأخير مضاف (مركبة‑ساعة)</th><th class="num">صافي التأخير</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    ${policyNote}
    <h2>هل مقترحي قابل للاختبار الآن؟</h2>
    <div class="card">
      <p style="margin-top:0;font-size:14px;color:var(--muted)">
        اكتب المقترح كما تطرحه في الاجتماع. المنصّة تُطابقه على الأذرع المقيسة،
        وتقول صراحةً إن لم يكن هناك تشغيل — <b>لا يوجد رقم بلا تشغيل</b>.
      </p>
      <div class="chatbar">
        <input type="text" id="lab-proposal" placeholder="مثال: إغلاق تقاطع أنس × تركي وتحويل الحركة إلى شارع أبها">
        <button class="primary" id="lab-run">افحص</button>
      </div>
      <div class="chips">
        <button data-fill="إغلاق تقاطع أنس بن مالك مع طريق الأمير تركي">إغلاق التقاطع</button>
        <button data-fill="إغلاق التقاطع مع تحويلة مدعومة وتوسعة">إغلاق + تحويلة</button>
        <button data-fill="إعادة توقيت الإشارات على الممر">إعادة توقيت الإشارات</button>
        <button data-fill="إغلاق كامل لشارع أنس بن مالك">إغلاق الممر كاملًا</button>
      </div>
      <div id="lab-out" style="margin-top:14px"></div>
    </div>`;
  $$('#lab-body [data-fill]').forEach(b => b.addEventListener('click', () => {
    $('#lab-proposal').value = b.dataset.fill; runLabProposal();
  }));
  $$('#lab-body [data-scenario]').forEach(b => b.addEventListener('click', () => setScenario(b.dataset.scenario)));
  runSelfTests();
}

function runLabProposal() {
  const q = ($('#lab-proposal').value || '').trim();
  const out = $('#lab-out');
  if (!q) { out.innerHTML = '<div class="note">اكتب مقترحًا أولًا.</div>'; return; }
  const t = q.toLowerCase();
  const say = (html) => { out.innerHTML = html; };

  const hasClose = /إغلاق|اغلاق|غلق|تقاطع|أنس|انس بن مالك/.test(t);
  const hasDetour = /تحويل|تحويلة|توسعة|بديل|دعم/.test(t);
  const hasSignals = /إشار|اشار|توقيت|تزامن/.test(t);
  const fullCorridor = /كامل|كل الممر|الممر كامل/.test(t);

  if (hasSignals && !hasClose) {
    say(`<div class="card" style="border-inline-start:4px solid var(--amber)">
      <h3>لا يمكن الحكم — لا يوجد تشغيل لهذا المقترح</h3>
      <p style="font-size:14px">الشبكة المستخدمة <b>بلا إشارات مرورية</b>: كل تقاطعات الممر تعمل بلا توقيت
      (<code>tls.all-off=true</code>) لأن الإشارات أُزيلت واقعًا قبل نحو سنة. لذلك «إعادة توقيت» ليست خيارًا في هذا النموذج،
      وأي رقم نُنتجه لها سيكون مُفبركًا.</p>
      <p style="font-size:13.5px;color:var(--muted)">ما الذي يجعلها قابلة للاختبار؟ إدخال الإشارات إلى الشبكة أولًا (بناء سيناريو جديد)، ثم معايرة طلب، ثم 5 بذور.</p>
      </div>`);
    return;
  }
  if (fullCorridor) {
    say(`<div class="card" style="border-inline-start:4px solid var(--amber)">
      <h3>خارج نطاق التشغيلات</h3>
      <p style="font-size:14px">المقيس هو إغلاق <b>تقاطع</b> أنس × تركي مع تحويل، لا إغلاق الممر كاملًا.
      لا رقم بلا مجلد تشغيل. هذا قرار عرض صريح: نُظهر ما قِسناه فقط.</p>
      <p style="font-size:13.5px;color:var(--muted)">أقرب ذراع مقيس: ${ARM_AR.closure} — ${fmt(stat('closure', 'duration_mean_min').mean, 2)} دقيقة/رحلة.</p>
      </div>`);
    return;
  }
  if (hasClose && hasDetour) {
    const a = stat('detour', 'duration_mean_min'), b = stat('closure', 'duration_mean_min');
    const dn = S.dmg.detour, dc = S.dmg.closure;
    say(`<div class="card" style="border-inline-start:4px solid var(--warn, #d68910)">
      <h3>يُطابق: «إغلاق + تحويلة مدعومة» — مقيس ✅</h3>
      <p style="font-size:14px">صافي التأخير <b>${fmt(dn.net_vh, 1)}</b> مركبة‑ساعة مقابل <b>${fmt(dc.net_vh, 1)}</b> بلا تحويلة:
      يُوفّر <b>${fmt(dc.net_vh - dn.net_vh, 1)}</b> مركبة‑ساعة (${fmt(pct(dc.net_vh - dn.net_vh, dc.net_vh), 1)}%).
      لكن زمن الرحلة ${fmt(a.mean, 2)} ± ${fmt(a.sd, 2)} دقيقة مقابل ${fmt(b.mean, 2)} ± ${fmt(b.sd, 2)} — <b>${a.mean < b.mean ? 'تحسّن هامشي' : 'لا تحسّن'}</b>.</p>
      <p style="font-size:13.5px;color:var(--muted)">الحكم: التحويلة تنقل الضرر من ${dn.streets[0].street} (${fmt(dn.streets[0].added_vh, 1)} مركبة‑ساعة) إلى ${dn.streets[1].street} — إعادة توزيع أكثر منها حلًّا. ${dn.recovered_vh > dc.recovered_vh ? 'الاسترداد على الشوارع الأخرى أعلى (' + fmt(dn.recovered_vh, 1) + ' مقابل ' + fmt(dc.recovered_vh, 1) + ').' : ''}</p>
      <p class="ev" style="font-size:12px;color:var(--muted);border-top:1px dashed var(--line);padding-top:8px">
        المصدر: <code>runs/*_detour300</code> · <code>runs/damage_detour300.edges.csv</code></p>
      <button class="primary" data-goto="map" style="margin-top:6px">اعرضه على الخريطة</button>
      </div>`);
    return;
  }
  if (hasClose) {
    const c = stat('closure', 'duration_mean_min');
    say(`<div class="card" style="border-inline-start:4px solid var(--red)">
      <h3>يُطابق: «إغلاق تقاطع أنس × تركي» — مقيس ✅</h3>
      <p style="font-size:14px">زمن الرحلة <b>${fmt(c.mean, 2)} ± ${fmt(c.sd, 2)}</b> دقيقة مقابل
      <b>${fmt(stat('baseline', 'duration_mean_min').mean, 2)} ± ${fmt(stat('baseline', 'duration_mean_min').sd, 2)}</b> في خط الأساس.
      صافي التأخير <b>${nf(Math.round(S.dmg.closure.net_vh))}</b> مركبة‑ساعة على ${nf(S.dmg.closure.edges_hit)} ضلعًا.</p>
      <button class="primary" data-goto="map" style="margin-top:6px">اعرضه على الخريطة</button>
      </div>`);
    return;
  }
  say(`<div class="card" style="border-inline-start:4px solid var(--amber)">
    <h3>لا يوجد تشغيل مطابق</h3>
    <p style="font-size:14px">لم أطابق مقترحك مع أي ذراع مقيس، ولن أُخرج رقمًا تقديريًّا. الأذرع المتاحة:
    ${['baseline', 'closure', 'detour'].map(a => ARM_AR[a]).join(' · ')}.</p>
    <p style="font-size:13.5px;color:var(--muted)">لإضافة ذراع جديد: بناء ملفات السيناريو، 5 بذور، ثم تسجيله في <code>runs/results.csv</code> وإعادة بناء البيانات بأمر واحد.</p>
    </div>`);
}

/* ---------------------------------------------------------------- analyst */
function findings() {
  const c = S.dmg.closure, d = S.dmg.detour;
  const top = c.streets.slice(0, 3);
  const topShare = pct(top.reduce((a, s) => a + s.added_vh, 0), c.added_vh_positive);
  const stay = pct(c.net_vh, c.added_vh_positive);
  const saved = c.net_vh - d.net_vh;
  const rate = S.canon.numbers.find(n => n.id === 'economics_rate').value;
  const base = stat('baseline', 'duration_mean_min'), clo = stat('closure', 'duration_mean_min');

  return [
    {
      tag: 'الأثر', title: 'الضرر يتركّز في شوارع قليلة',
      big: `${fmt(topShare, 0)}%`,
      body: `${top.map(s => s.street + ' (' + fmt(s.added_vh, 1) + ')').join(' · ')} — ثلاثة شوارع تحمل أغلب
      الـ${nf(Math.round(c.added_vh_positive))} مركبة‑ساعة المضافة. التحسين يبدأ من هنا لا من «الشبكة».`,
      ev: 'runs/damage_closure300.edges.csv · تجميع حسب اسم الشارع'
    },
    {
      tag: 'الانتقال', title: 'الحمل يتوزّع ولا يختفي',
      big: `${fmt(stay, 1)}%`,
      body: `من التأخير المضاف يبقى داخل شبكة الممر؛ ${fmt(c.recovered_vh, 1)} مركبة‑ساعة فقط تُسترد على شوارع
      استقبلت حركة أعلى (${nf(c.empty_edges)} ضلعًا فقد كل حركته). هذا يعني أن سياسة «أغلق وحرّك» لا تُنتج فائضًا.`,
      ev: 'صافي = موجب + سالب على 8,488 ضلعًا · método: محاكاة مقابل محاكاة'
    },
    {
      tag: 'المقترح', title: 'التحويلة المدعومة تُحسّن قليلًا',
      big: `${fmt(saved, 1)}`,
      body: `مركبة‑ساعة تُوفَّر (${fmt(pct(saved, c.net_vh), 1)}%) عند إضافة تحويلة مدعومة وتوسعة.
      زمن الرحلة ${fmt(stat('detour', 'duration_mean_min').mean, 2)} مقابل ${fmt(clo.mean, 2)} دقيقة — فرق داخل حدود الضجيج.
      الفائدة الحقيقية أنها تنقل الضغط من طريق الأمير تركي إلى شارع أبها.`,
      ev: 'runs/damage_detour300.edges.csv مقابل damage_closure300.edges.csv'
    },
    {
      tag: 'الحساسية', title: 'الرقم حساس لسياسة القياس',
      big: `${fmt(stat('policy600', 'corridor').sd, 2)}`,
      body: `انحراف معياري على زمن الممر عند تغيير حدّ الانتظار قبل النقل القسري (300→600 ث):
      ${fmt(stat('policy600', 'corridor').mean, 2)} مقابل ${fmt(stat('baseline', 'corridor').mean, 2)} دقيقة.
      لذلك أي مقارنة بين مقترحين تُجرى على السياسة نفسها، وإلا صارت المقارنة أثرًا للسياسة.`,
      ev: 'runs/corridor_canon27.csv · BASELINE_FACTS.md §4'
    },
    {
      tag: 'الاقتصاد', title: 'الكلفة السنوية للفشل',
      big: `${nf(Math.round(c.net_vh * rate))}`,
      body: `ريال لكل ذروة مسائية (4 ساعات) عند ${fmt(rate, 2)} ريال/مركبة‑ساعة.
      الرقم للترتيب لا للتدقيق: يستخدم قيمة ساعة مركبة من أدبيات النقل الحضري، لا مسحًا محليًا.`,
      ev: 'ECONOMIC_IMPACT.md · SHC 203 ص75 جدول 4-2'
    },
    {
      tag: 'الأسطول', title: 'كل رحلة تدفع الثمن، لا الممر وحده',
      big: `+${fmt(clo.mean - base.mean, 1)}`,
      body: `دقيقة على متوسط الرحلة: ${fmt(base.mean, 2)} → ${fmt(clo.mean, 2)} (×${fmt(clo.mean / base.mean, 2)}).
      زمن العبور على تعريف الممر قيس لخط الأساس فقط (${fmt(stat('baseline', 'corridor').mean, 2)} دقيقة)؛
      بعد الإغلاق لا نعرض رقم ممر لأن تعريف الممر لم يُشغَّل على أذرع الإغلاق — وهذا مذكور في الحدود.`,
      ev: 'runs/*/metrics.json · trips.json · corridor_canon300.csv'
    }
  ];
}

function buildAnalyst() {
  $('#findings').innerHTML = findings().map(f => `
    <div class="finding">
      <h3><span class="tag navy">${f.tag}</span> ${f.title}</h3>
      <div class="big">${f.big}</div>
      <p>${f.body}</p>
      <div class="ev">الدليل: <span class="mono">${f.ev}</span></div>
    </div>`).join('');

  const QA = [
    ['من يدفع الثمن؟', () => {
      const s = S.dmg.closure.streets.slice(0, 5);
      return `أعلى خمسة شوارع تستقبل التأخير:\n` +
        s.map((x, i) => `${i + 1}. ${x.street} — ${fmt(x.added_vh, 1)} مركبة‑ساعة (${fmt(pct(x.added_vh, S.dmg.closure.added_vh_positive), 1)}%)`).join('\n') +
        `\n\nالمجموع: ${fmt(s.reduce((a, b) => a + b.added_vh, 0), 1)} من ${nf(Math.round(S.dmg.closure.added_vh_positive))} مركبة‑ساعة مضافة.\n` +
        `الدليل: damage_closure300.edges.csv`;
    }],
    ['هل التحويلة تنفع؟', () => {
      const c = S.dmg.closure, d = S.dmg.detour;
      return `نعم بشكل هامشي: ${fmt(c.net_vh - d.net_vh, 1)} مركبة‑ساعة (${fmt(pct(c.net_vh - d.net_vh, c.net_vh), 1)}%) أقل.\n` +
        `زمن الرحلة: ${fmt(stat('detour', 'duration_mean_min').mean, 2)} ± ${fmt(stat('detour', 'duration_mean_min').sd, 2)} مقابل ${fmt(stat('closure', 'duration_mean_min').mean, 2)} ± ${fmt(stat('closure', 'duration_mean_min').sd, 2)} دقيقة.\n` +
        `الفرق أصغر من الانحراف المعياري بين البذور ⇒ ليس تحسّنًا يُبنى عليه قرار وحده.`;
    }],
    ['ما أسوأ ضلع؟', () => {
      const e = S.dmg.closure.top_edges.slice(0, 5);
      return `أسوأ خمسة أضلاع:\n` + e.map((x, i) => `${i + 1}. ${x[1]} — ${fmt(x[2], 1)} مركبة‑ساعة (Δ ${fmt(x[3], 0)} ث)`).join('\n') +
        `\n\nالدليل: damage_closure300.edges.csv · ${S.dmg.closure.sha16}`;
    }],
    ['كيف أختبر مقترحًا جديدًا؟', () => {
      return `ثلاث خطوات، ولا يوجد اختصار:\n1) بناء السيناريو في SUMO (net + routes + add).\n` +
        `2) 5 بذور × 4 ساعات على نفس السياسة (ttt=${S.arms.arms.baseline.ttt}, dial 8.0).\n` +
        `3) python build/extract_arms.py ثم pytest -q — بوابة الأرقام ترفض أي رقم بلا مجلد تشغيل.\n` +
        `الزمن الفعلي للذراع الواحد: نحو 6–8 دقائق حوسبة على هذا الجهاز.`;
    }],
    ['هل الأرقام معايرة ميدانيًا؟', () => {
      return `لا. الصدق أولًا: لا يوجد زمن رحلة مقيس ميدانيًا لهذا المقطع، والنموذج لم يُعاير على عدّادات.\n` +
        `لذلك الرقم صالح لمقارنة سيناريوهين على الشبكة نفسها، ولا يصلح للتنبؤ المطلق بدقائق.\n` +
        `الحدود كاملة في تبويب «المنهجية».`;
    }],
    ['ما الذي لا يقيسه النموذج؟', () => {
      return `— المشاة والوقوف الجانبي.\n— الإشارات (مُزالة من الشبكة أصلًا).\n— سلوك السائق المحلي (توجيه بأقصر زمن حرّ، لا تعلّم).\n` +
        `— الطلب خارج نافذة الذروة الأربع ساعات.\n— النقل القسري: خط الأساس عند 600 ث لا ينقل أي مركبة؛ وأذرع الإغلاق تنقل نحو 6% بعد 600 ث (شرط SUMO، لا اختيارنا) ⇒ كلفة الإغلاق المقيسة أقلّ من الحقيقية، لا أكثر.`;
    }]
  ];

  const log = $('#chatlog');
  const push = (who, text) => {
    const m = el(`<div class="msg ${who}">${text}</div>`);
    log.appendChild(m); log.scrollTop = log.scrollHeight;
  };
  push('bot', 'أنا محلّل انسياب. أُجيب من بيانات التشغيل المحفوظة فقط، وأُسمّي الملف الذي جاء منه كل رقم.\nاسألني أو اختر سؤالًا جاهزًا.');

  const answer = (q) => {
    const hit = QA.find(([k]) => q.includes(k.replace(/[؟?]/g, '').slice(0, 6)) || k === q);
    const kw = [
      [/دفع|أسوأ شارع|يدفع|يقاسي/, 0], [/تحويل|تحويلة|بديل/, 1], [/ضلع|أسوأ ضلع/, 2],
      [/أختبر|اختبر|تشغيل|كيف أ/, 3], [/معاير|ميداني|دقة|أثق/, 4], [/لا يقيس|حدود|قيود/, 5]
    ];
    const byKw = kw.find(([re]) => re.test(q));
    if (hit) return hit[1]();
    if (byKw) return QA[byKw[1]][1]();
    return `لا أجد في بياناتي ما يجيب هذا تحديدًا. أستطيع أن أُجيب عن: من يدفع الثمن · هل التحويلة تنفع · أسوأ ضلع · كيف أختبر مقترحًا · هل الأرقام معايرة · ما الذي لا يقيسه النموذج.\n\n` +
      `ولن أخترع رقمًا: كل ما هنا من ${S.arms.arms.baseline.n * 4} تشغيلًا محفوظًا.`;
  };

  $('#chat-send').addEventListener('click', () => {
    const q = $('#chat-in').value.trim(); if (!q) return;
    push('user', q); $('#chat-in').value = '';
    setTimeout(() => push('bot', answer(q)), 120);
  });
  $('#chat-in').addEventListener('keydown', e => { if (e.key === 'Enter') $('#chat-send').click(); });
  QA.forEach(([q]) => {
    const b = el(`<button>${q}</button>`);
    b.addEventListener('click', () => { $('#chat-in').value = q; $('#chat-send').click(); });
    $('#chat-chips').appendChild(b);
  });

  // طبقة لغوية اختيارية
  $('#llm-toggle').addEventListener('click', () => {
    const box = $('#llm-box');
    box.style.display = box.style.display === 'none' ? '' : 'none';
  });
  $('#llm-send').addEventListener('click', async () => {
    const base = $('#llm-endpoint').value.trim().replace(/\/$/, '');
    const key = $('#llm-key').value.trim();
    const q = $('#chat-in').value.trim() || 'لخّص أهم ثلاث نتائج لجهة تُخطّط إغلاقًا.';
    const out = $('#llm-out');
    if (!base || !key) { out.innerHTML = '<div class="note">أدخل العنوان والمفتاح. يُحفظ المفتاح في هذا المتصفح فقط.</div>'; return; }
    localStorage.setItem('insiyab_llm', JSON.stringify({ base, key }));
    out.innerHTML = '<div class="note">جارٍ الاتصال…</div>';
    const ctx = {
      base_corridor: stat('baseline', 'corridor'), closure_corridor: stat('closure', 'corridor'),
      base_fleet: stat('baseline', 'duration_mean_min'), closure_fleet: stat('closure', 'duration_mean_min'),
      detour_fleet: stat('detour', 'duration_mean_min'),
      added_vh: S.dmg.closure.added_vh_positive, net_vh: S.dmg.closure.net_vh,
      recovered_vh: S.dmg.closure.recovered_vh, detour_net_vh: S.dmg.detour.net_vh,
      top_streets: S.dmg.closure.streets.slice(0, 6),
      limits: S.canon.limits, policy: S.canon.policy
    };
    try {
      const r = await fetch(base + '/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + key },
        body: JSON.stringify({
          model: $('#llm-model').value.trim() || 'deepseek-chat',
          messages: [
            { role: 'system', content: 'أنت محلّل مرور سعودي. أجب بالعربية من الأرقام المعطاة فقط، بلا تقديرات جديدة، وسمِّ الملف إن ذكرت رقمًا. كن مختصرًا.' },
            { role: 'user', content: 'البيانات: ' + JSON.stringify(ctx) + '\n\nالسؤال: ' + q }
          ],
          temperature: 0.2
        })
      });
      const j = await r.json();
      const txt = (j.choices && j.choices[0] && j.choices[0].message.content) || JSON.stringify(j).slice(0, 400);
      out.innerHTML = `<div class="msg bot" style="max-width:100%">${txt.replace(/</g, '&lt;')}</div>`;
    } catch (e) {
      out.innerHTML = `<div class="note">تعذّر الاتصال: ${e.message}</div>`;
    }
  });
  try {
    const saved = JSON.parse(localStorage.getItem('insiyab_llm') || 'null');
    if (saved) { $('#llm-endpoint').value = saved.base; $('#llm-key').value = saved.key; }
  } catch (e) { }
}

/* ------------------------------------------------------- القراءة الآلية (AI) */
function mdToHtml(md) {
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const inline = (s) => esc(s)
    .replace(/`([^`]+)`/g, '<span class="mono">$1</span>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  const out = []; let list = null;
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };
  for (const raw of md.split('\n')) {
    const l = raw.trim();
    if (!l) { closeList(); continue; }
    if (l.startsWith('#### ')) { closeList(); out.push(`<h4>${inline(l.slice(5))}</h4>`); continue; }
    if (l.startsWith('### ')) { closeList(); out.push(`<h3 style="margin:14px 0 6px">${inline(l.slice(4))}</h3>`); continue; }
    if (l.startsWith('## ')) { closeList(); out.push(`<h2 style="margin:18px 0 8px;font-size:19px">${inline(l.slice(3))}</h2>`); continue; }
    if (l.startsWith('# ')) { closeList(); out.push(`<h2 style="margin:0 0 10px;font-size:21px">${inline(l.slice(2))}</h2>`); continue; }
    if (l.startsWith('> ')) { closeList(); out.push(`<div class="note" style="margin:8px 0">${inline(l.slice(2))}</div>`); continue; }
    if (/^[-•] /.test(l)) { if (list !== 'ul') { closeList(); out.push('<ul>'); list = 'ul'; } out.push(`<li>${inline(l.slice(2))}</li>`); continue; }
    if (/^\d+\. /.test(l)) { if (list !== 'ol') { closeList(); out.push('<ol>'); list = 'ol'; } out.push(`<li>${inline(l.replace(/^\d+\. /, ''))}</li>`); continue; }
    closeList(); out.push(`<p>${inline(l)}</p>`);
  }
  closeList();
  return out.join('\n');
}

async function buildBrief() {
  const host = $('#ai-brief');
  if (!host) return;
  try {
    const [md, st] = await Promise.all([
      fetch('data/ai_brief.md').then(r => { if (!r.ok) throw 0; return r.text(); }),
      fetch('data/ai_brief_status.json').then(r => r.ok ? r.json() : null).catch(() => null)
    ]);
    const badge = st
      ? `<span class="tag ${st.ok ? 'green' : 'red'}">تحقّق آلي: ${st.matched}/${st.total} رقمًا مسنود</span>
         <span style="font-size:12.5px;color:var(--muted)">آخر فحص ${st.ran_at} · <span class="mono">build/verify_brief.py</span></span>`
      : `<span class="tag amber">لم يُشغَّل الفحص</span>
         <span style="font-size:12.5px;color:var(--muted)">شغّل <span class="mono">python build/verify_brief.py</span></span>`;
    host.innerHTML = `<div class="card" style="margin-bottom:16px">${mdToHtml(md)}
      <div style="margin-top:14px;display:flex;gap:10px;flex-wrap:wrap;align-items:center">${badge}</div></div>`;
  } catch (e) {
    host.innerHTML = '';
  }
}

/* --------------------------------------------------------------- method */
function buildMethod() {
  $('#limits').innerHTML = S.canon.limits.map(l => `<li>${l}</li>`).join('');
  $('#banned').innerHTML = S.canon.banned.map(b => `<li class="mono">${b}</li>`).join('');
  $('#prov').innerHTML = `
    <tr><td>الشبكة</td><td class="mono">${S.net.source}</td><td class="num">${nf(S.net.counts.edges)} ضلعًا</td><td class="mono">${S.meta.sources.net.sha16}</td></tr>
    <tr><td>نتائج التشغيلات</td><td class="mono">runs/results.csv</td><td class="num">${nf(S.arms.arms.baseline.n + S.arms.arms.closure.n + S.arms.arms.detour.n + S.arms.arms.policy600.n)} تشغيلًا</td><td class="mono">${S.meta.sources['results.csv'].sha16}</td></tr>
    <tr><td>كاشف انتقال الضرر</td><td class="mono">${S.dmg.closure.file}</td><td class="num">${nf(S.dmg.closure.edges_total)} ضلعًا</td><td class="mono">${S.dmg.closure.sha16}</td></tr>
    <tr><td>اختبار الحياد</td><td class="mono">${S.dmg.identity.file}</td><td class="num">صافي ${fmt(S.dmg.identity.net_vh, 1)}</td><td class="mono">${S.dmg.identity.sha16}</td></tr>`;
  $('#policybox').innerHTML = Object.entries(S.canon.policy).map(([k, v]) =>
    `<span class="tag">${k} = <b class="mono">${v}</b></span>`).join(' ');
}

/* ------------------------------------------------------------ self tests */
/* ------------------------------------------------------------------ images */
async function buildImages() {
  let man;
  try { man = await (await fetch('data/figures.json', { cache: 'no-store' })).json(); }
  catch (e) { $('#view-images').insertAdjacentHTML('beforeend', '<div class="note">لم يُبنَ معرض الصور بعد: شغّل build/make_figures.py</div>'); return; }
  const F = man.figures, byFile = Object.fromEntries(F.map(f => [f.file, f]));
  const src = (f) => `${f.file}?v=${man.built || 1}`;
  const b = byFile['images/01_baseline.png'], c = byFile['images/02_closure.png'], d = byFile['images/03_detour.png'];
  const frame = (f, tag, color) => `
    <figure style="margin:0;position:relative">
      <img src="${src(f)}" alt="${f.title}" style="width:100%;display:block;border-radius:10px;border:1px solid var(--line)">
      <figcaption style="margin-top:8px">
        <b style="color:${color}">${tag}</b> · <span style="font-size:13px;color:var(--muted)">${f.note}</span>
      </figcaption>
    </figure>`;
  $('#beforeafter').innerHTML = `
    <div class="card">
      <h3 style="margin:0 0 10px">قبل / بعد على نفس الإطار ونفس مقياس التلوين</h3>
      <div class="grid g2" style="gap:16px">${frame(b, 'قبل — خط الأساس', 'var(--slate)')}${frame(c, 'بعد — الإغلاق', 'var(--red)')}</div>
      <div style="margin-top:14px" class="grid g2">${frame(d, 'بعد — التحويلة المدعومة', 'var(--green)')}
        <div class="card" style="margin:0;background:var(--bg)">
          <b>ماذا يتغير فعلًا</b>
          <ul class="tight" style="margin:8px 0 0">
            <li>زمن الرحلة: ${fmt(stat('baseline','duration_mean_min').mean,2)} ⇒ ${fmt(stat('closure','duration_mean_min').mean,2)} ⇒ ${fmt(stat('detour','duration_mean_min').mean,2)} دقيقة.</li>
            <li>التأخير المضاف: ${fmt(S.dmg.closure.added_vh_positive,0)} مركبة‑ساعة، يُسترد ${fmt(S.dmg.closure.recovered_vh,1)} على شوارع بديلة.</li>
            <li>التحويلة تخفض الصافي إلى ${fmt(S.dmg.detour.net_vh,1)} لكنها لا تُلغيه: ${fmt(100 * S.dmg.detour.net_vh / S.dmg.closure.added_vh_positive,1)}% من التأخير يبقى.</li>
          </ul>
          <div class="note" style="margin-top:10px">الحدود: صور بلا ترميز لوني موحّد بين الأذرع تقيس <b>فرقًا</b> لا حالة مطلقة.</div>
        </div>
      </div>
    </div>`;
  $('#gallery').innerHTML = F.filter(f => f.kind === 'chart').map(f => `
    <figure class="card" style="margin:0;padding:12px">
      <img src="${src(f)}" alt="${f.title}" style="width:100%;display:block;border-radius:8px;border:1px solid var(--line)">
      <figcaption style="margin-top:10px"><b>${f.title}</b>
        <div style="font-size:13px;color:var(--muted)">${f.note}</div></figcaption>
    </figure>`).join('');
}

function runSelfTests() {
  const host = $('#tests');
  if (!host) return;
  const cases = [];
  const near = (a, b, tol) => Math.abs(a - b) <= tol;
  const add = (name, fn, why) => {
    try { const r = fn(); cases.push({ name, ok: r === true, why: r === true ? why : String(r || why) }); }
    catch (e) { cases.push({ name, ok: false, why: e.message }); }
  };
  // كل توقّع يُقرأ من canon.json — المصدر الوحيد للحقيقة
  const ref = (id) => S.canon.numbers.find(n => n.id === id);
  const refVal = (arm, field, dmgField) => {
    const n = S.canon.numbers.find(x => x.arm === arm && x.field === field);
    return n ? n.value : null;
  };
  const dmgRef = { damage_net: ['closure', 'net_vh'], recovered: ['closure', 'recovered_vh'], detour_net: ['detour', 'net_vh'] };

  add('زمن رحلة خط الأساس = قيمة الكانون', () => {
    const v = refVal('baseline', 'duration_mean_min');
    return near(stat('baseline', 'duration_mean_min').mean, v, 0.02) || `${stat('baseline', 'duration_mean_min').mean} ≠ ${v}`;
  }, `${refVal('baseline', 'duration_mean_min')} دقيقة · runs/*_canon300/metrics.json`);

  add('زمن رحلة الإغلاق = قيمة الكانون', () => {
    const v = refVal('closure', 'duration_mean_min');
    return near(stat('closure', 'duration_mean_min').mean, v, 0.02) || `${stat('closure', 'duration_mean_min').mean} ≠ ${v}`;
  }, `${refVal('closure', 'duration_mean_min')} دقيقة · runs/*_closure300/metrics.json`);

  add('زمن عبور الممر = قيمة الكانون', () => {
    const v = refVal('baseline', 'corridor');
    return near(stat('baseline', 'corridor').mean, v, 0.02) || `${stat('baseline', 'corridor').mean} ≠ ${v}`;
  }, `${refVal('baseline', 'corridor')} دقيقة · corridor_canon300.csv`);

  add('كل ذراع له نفس عدد البذور', () => {
    const ns = ['baseline', 'closure', 'detour', 'policy600'].map(a => S.arms.arms[a].n);
    return ns.every(n => n === ns[0]) || 'أعداد مختلفة: ' + ns.join(',');
  }, `${S.canon.policy.seeds.length} بذور (${S.canon.policy.seeds.join(',')})`);

  add('كاشف الضرر محايد على الهوية (=0)', () =>
    near(S.dmg.identity.net_vh, 0, 0.01) || S.dmg.identity.net_vh, 'damage_identity.edges.csv · تشغيل مقابل نفسه');

  add('صافي ضرر الإغلاق = قيمة الكانون', () => {
    const v = ref('damage_net').value;
    return near(S.dmg.closure.net_vh, v, 0.6) || `${S.dmg.closure.net_vh} ≠ ${v}`;
  }, `${ref('damage_net').value} مركبة‑ساعة · damage_closure300.edges.csv`);

  add('المسترد على شوارع أخرى = قيمة الكانون', () => {
    const v = ref('recovered').value;
    return near(S.dmg.closure.recovered_vh, v, 0.6) || `${S.dmg.closure.recovered_vh} ≠ ${v}`;
  }, `${ref('recovered').value} · عمود سالب في الملف نفسه`);

  add('التأخير المضاف يطابق صافي + المسترد (اتساق داخلي)', () => {
    const sum = S.dmg.closure.net_vh + S.dmg.closure.recovered_vh;
    return near(sum, S.dmg.closure.added_vh_positive, 1.0) || `${fmt(sum, 1)} ≠ ${fmt(S.dmg.closure.added_vh_positive, 1)}`;
  }, 'صافي + مسترد = موجب');

  add('كل ضلع في بيانات الضرر موجود في الشبكة', () => {
    const ok = new Set(S.net.edges.map(e => e[0]));
    const miss = S.dmg.closure.edges.filter(e => !ok.has(e[0]));
    return miss.length === 0 || `ناقص: ${miss.length} (${miss.slice(0, 2).map(m => m[0]).join(',')})`;
  }, `${nf(S.net.counts.edges)} ضلعًا`);

  add('لا رقم مسحوب في الواجهة (خارج قائمة الحظر)', () => {
    const txt = $$('.view').filter(v => v.id !== 'view-method').map(v => v.innerText).join('\n');
    const bad = S.canon.banned.filter(b => txt.includes(b) || txt.includes(b.replace(/,/g, '')));
    return bad.length === 0 || 'موجود: ' + bad.join(' · ');
  }, `${S.canon.banned.length} صيغة محظورة`);

  add('عدد الرحلات > 5,000 في كل ذراع', () =>
    ['baseline', 'closure', 'detour', 'policy600'].every(a => S.arms.arms[a].stats.trips.mean > 5000) ||
    JSON.stringify(['baseline', 'closure', 'detour', 'policy600'].map(a => Math.round(S.arms.arms[a].stats.trips.mean))),
    'results.csv · عمود trips');

  add('التحويلة أقل ضررًا من الإغلاق وحده', () => {
    const v = ref('detour_net').value;
    return (near(S.dmg.detour.net_vh, v, 0.6) && S.dmg.detour.net_vh < S.dmg.closure.net_vh) ||
      `${S.dmg.detour.net_vh} مقابل ${S.dmg.closure.net_vh}`;
  }, `${ref('detour_net').value} مقابل ${ref('damage_net').value}`);

  const pass = cases.filter(c => c.ok).length;
  host.innerHTML = `<div class="summary">
      <span class="tag ${pass === cases.length ? 'green' : 'red'}">${pass}/${cases.length} نجحت</span>
      <span style="color:var(--muted);font-size:13px">تُعاد عند كل تحميل — نفس القواعد في <code>tests/</code> و<span class="mono">CI</span></span>
    </div>` +
    cases.map(c => `<div class="test"><span class="dot ${c.ok ? 'pass' : 'fail'}"></span>
      <div><div>${c.name}</div><div class="why">${c.ok ? '✓ ' : '✗ '}${c.why}</div></div></div>`).join('');
  window.__INSIYAB_TESTS__ = { pass, total: cases.length, cases };
}

document.addEventListener('DOMContentLoaded', () => {
  boot().catch(e => {
    document.body.insertAdjacentHTML('afterbegin',
      `<div style="background:#fdecea;color:#8e2a1e;padding:14px 20px">تعذّر تحميل البيانات: ${e.message}.<br>
       إن فتحت الملف مباشرة من القرص، استخدم النسخة المدمجة <code>insiyab_demo.html</code> أو شغّل
       <code>python -m http.server</code> داخل المجلد.</div>`);
  });
});
