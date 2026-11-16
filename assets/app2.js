/* انسياب — محرك النموذج الأولي (الجيل الثاني)
   يقرأ كل رقم من data/anas.json و data/junction.json — لا رقم مكتوب هنا. */
(function () {
  'use strict';

  var R = 6371008.8;
  var TZ = 3 * 3600;                      // الرياض = UTC+3 بلا توقيت صيفي
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var S = {
    data: null, junc: null,
    lon0: 0, lat0: 0, scale: 1, tx: 0, ty: 0,
    W: 0, H: 0, dpr: Math.min(2, window.devicePixelRatio || 1),
    idx: 0, drawn: 0, playing: false, mult: 120, vt: 0,
    seg: 'all', segBox: null,
    base: null, path: null, bctx: null, pctx: null,
    cum: [], grid: null, gridCell: 0.0009, gridO: { lon: 0, lat: 0 }
  };

  /* ── أدوات ── */
  function hav(a, b) {
    var p1 = a[1] * Math.PI / 180, p2 = b[1] * Math.PI / 180;
    var dp = p2 - p1, dl = (b[0] - a[0]) * Math.PI / 180;
    var h = Math.sin(dp / 2) * Math.sin(dp / 2) +
            Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) * Math.sin(dl / 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  function hhmmss(sec) {
    var d = new Date((sec + TZ) * 1000);
    var p = function (n) { return (n < 10 ? '0' : '') + n; };
    return p(d.getUTCHours()) + ':' + p(d.getUTCMinutes()) + ':' + p(d.getUTCSeconds());
  }
  function fmt(n, d) { return (Math.round(n * Math.pow(10, d)) / Math.pow(10, d)).toFixed(d); }

  /* ── الإسقاط ── */
  function wx(lon) { return (lon - S.lon0) * 111320 * Math.cos(S.lat0 * Math.PI / 180); }
  function wy(lat) { return -(lat - S.lat0) * 110540; }
  function px(lon) { return S.tx + wx(lon) * S.scale; }
  function py(lat) { return S.ty + wy(lat) * S.scale; }

  function fit(box) {                      // box = [lonMin, latMin, lonMax, latMax]
    var w = (box[2] - box[0]) * 111320 * Math.cos(S.lat0 * Math.PI / 180);
    var h = (box[3] - box[1]) * 110540;
    var sx = (S.W * 0.9) / Math.max(1e-6, w), sy = (S.H * 0.82) / Math.max(1e-6, h);
    S.scale = Math.min(sx, sy);
    S.lon0 = (box[0] + box[2]) / 2; S.lat0 = (box[1] + box[3]) / 2;
    S.tx = S.W / 2; S.ty = S.H / 2;
  }

  /* ── الشبكة: خلفية مجهّزة مرة واحدة ── */
  function makeCanvas() {
    var c = document.createElement('canvas');
    c.width = Math.round(S.W * S.dpr); c.height = Math.round(S.H * S.dpr);
    var x = c.getContext('2d'); x.setTransform(S.dpr, 0, 0, S.dpr, 0, 0);
    return [c, x];
  }

  function drawBase() {
    var t = makeCanvas(); S.base = t[0]; S.bctx = t[1];
    var g = S.bctx, d = S.data, net = $('#ly-net').checked, corr = $('#ly-corr').checked;
    g.clearRect(0, 0, S.W, S.H);
    g.lineCap = 'round';

    // أرضية خفيفة تحت الشبكة
    g.strokeStyle = 'rgba(43,58,74,.55)'; g.lineWidth = 1.1;
    for (var i = 0; i < d.edges.length; i++) {
      var e = d.edges[i];
      if (e.c ? !corr : !net) continue;
      var sh = d.shapes[e.s]; if (!sh || sh.length < 2) continue;
      var q = S.segBox;
      if (q && (sh[0][0] < q[0] - 0.03 || sh[0][0] > q[2] + 0.03)) continue;
      g.beginPath();
      g.moveTo(px(sh[0][0]), py(sh[0][1]));
      for (var k = 1; k < sh.length; k++) g.lineTo(px(sh[k][0]), py(sh[k][1]));
      g.stroke();
    }

    // ممر أنس: طبقة أوضح
    if (corr) {
      g.strokeStyle = 'rgba(84,120,150,.75)'; g.lineWidth = 2.1;
      for (var j = 0; j < d.edges.length; j++) {
        var c = d.edges[j]; if (!c.c) continue;
        var s2 = d.shapes[c.s]; if (!s2 || s2.length < 2) continue;
        g.beginPath(); g.moveTo(px(s2[0][0]), py(s2[0][1]));
        for (var m = 1; m < s2.length; m++) g.lineTo(px(s2[m][0]), py(s2[m][1]));
        g.stroke();
      }
    }

    // أثر الجولة كاملًا بخط باهت (يُبرز التقدّم عليه)
    if ($('#ly-path').checked) {
      var tr = S.data.trace.p;
      g.strokeStyle = 'rgba(55,224,164,.20)'; g.lineWidth = 2.2;
      g.beginPath(); g.moveTo(px(tr[0][1]), py(tr[0][2]));
      for (var v = 1; v < tr.length; v++) g.lineTo(px(tr[v][1]), py(tr[v][2]));
      g.stroke();
    }

    // موقع التقاطع
    if ($('#ly-junc').checked && d.junction && d.junction.lonlat) {
      var x = px(d.junction.lonlat[0]), y = py(d.junction.lonlat[1]);
      g.strokeStyle = 'rgba(255,176,32,.55)'; g.lineWidth = 1.4;
      g.beginPath(); g.arc(x, y, 15, 0, 6.2832); g.stroke();
      g.beginPath(); g.arc(x, y, 24, 0, 6.2832); g.stroke();
      g.fillStyle = 'rgba(255,176,32,.9)';
      g.beginPath(); g.arc(x, y, 3.4, 0, 6.2832); g.fill();
    }
    resetPath();
  }

  function resetPath() {
    var t = makeCanvas(); S.path = t[0]; S.pctx = t[1];
    S.drawn = 0;
  }

  function colorFor(v) {
    if (v < 10) return '#ff5d5d';
    if (v < 40) return '#ffb020';
    return '#37e0a4';
  }

  function extendPath(to) {
    var g = S.pctx, p = S.data.trace.p, seg = S.segBox;
    g.lineCap = 'round'; g.lineJoin = 'round'; g.lineWidth = 3.1;
    for (var i = S.drawn; i < to; i++) {
      var a = p[i], b = p[i + 1]; if (!b) break;
      if (seg && (a[1] < seg[0] || a[1] > seg[2])) continue;
      g.strokeStyle = colorFor(a[3]);
      g.beginPath(); g.moveTo(px(a[1]), py(a[2])); g.lineTo(px(b[1]), py(b[2])); g.stroke();
    }
    S.drawn = to;
  }

  /* ── الإطار ── */
  function frame() {
    var cv = $('#map'), ctx = cv.getContext('2d');
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    if (S.base) ctx.drawImage(S.base, 0, 0);
    if ($('#ly-path').checked && S.path) ctx.drawImage(S.path, 0, 0);

    var p = S.data.trace.p, i = Math.min(S.idx, p.length - 1), q = p[i];
    if ($('#ly-path').checked) {
      var x = px(q[1]), y = py(q[2]);
      // هالة
      var rg = ctx.createRadialGradient(x, y, 0, x, y, 26);
      rg.addColorStop(0, 'rgba(55,224,164,.45)'); rg.addColorStop(1, 'rgba(55,224,164,0)');
      ctx.fillStyle = rg; ctx.beginPath(); ctx.arc(x, y, 26, 0, 6.2832); ctx.fill();
      // جسم المركبة
      ctx.save(); ctx.translate(x, y);
      var b = bearing(p[Math.max(0, i - 3)], q);
      ctx.rotate(b * Math.PI / 180);
      ctx.fillStyle = '#eafff7';
      ctx.beginPath(); ctx.moveTo(0, -8.5); ctx.lineTo(5.4, 6.5); ctx.lineTo(0, 3.4); ctx.lineTo(-5.4, 6.5);
      ctx.closePath(); ctx.fill();
      ctx.restore();
    }
    updateHud(i);
    requestAnimationFrame(frame);
  }

  function bearing(a, b) {
    var y = Math.sin((b[1] - a[1]) * Math.PI / 180) * Math.cos(b[2] * Math.PI / 180);
    var x = Math.cos(a[2] * Math.PI / 180) * Math.sin(b[2] * Math.PI / 180) -
            Math.sin(a[2] * Math.PI / 180) * Math.cos(b[2] * Math.PI / 180) *
            Math.cos((b[1] - a[1]) * Math.PI / 180);
    return Math.atan2(y, x) * 180 / Math.PI;
  }

  function updateHud(i) {
    var p = S.data.trace.p, q = p[i], t0 = S.data.trace.t0;
    $('#hud-v').textContent = fmt(q[3], 0);
    $('#hud-t').textContent = hhmmss(t0 + q[0]);
    $('#hud-d').textContent = fmt(distTo(i) / 1000, 2);
    var f = i / Math.max(1, p.length - 1);
    $('#fill').style.width = (f * 100) + '%';
    $('#knob').style.insetInlineStart = (f * 100) + '%';
    $('#t-pos').textContent = hhmmss(t0 + q[0]);
  }

  function distTo(i) { return S.cum && S.cum[i] != null ? S.cum[i] : 0; }

  function buildCum() {
    var p = S.data.trace.p; S.cum = [0];
    for (var k = 1; k < p.length; k++) {
      S.cum[k] = S.cum[k - 1] + hav([p[k - 1][1], p[k - 1][2]], [p[k][1], p[k][2]]);
    }
  }

  /* ── التشغيل ── */
  var last = 0;
  function tick(ts) {
    if (!last) last = ts;
    var dt = Math.min(120, (ts - last) / 1000); last = ts;
    if (S.playing && S.data) {
      var p = S.data.trace.p;
      S.vt += dt * S.mult;
      var n = p.length - 1;
      while (S.idx < n && p[S.idx + 1][0] <= S.vt) S.idx++;
      if (S.idx >= n) { stop(); S.vt = p[n][0]; }
      extendPath(S.idx);
    }
    requestAnimationFrame(tick);
  }
  function play() { S.playing = true; $('#play').textContent = '❚❚'; }
  function stop() { S.playing = false; $('#play').textContent = '▶'; }

  /* ── الفهرس النصّي (اسم الشارع تحت المؤشر) ── */
  function buildIndex() {
    var d = S.data, g = {}, cell = S.gridCell;
    S.gridO.lon = d.bbox[0]; S.gridO.lat = d.bbox[1];
    for (var i = 0; i < d.edges.length; i++) {
      var e = d.edges[i], sh = d.shapes[e.s];
      if (!sh || !e.st) continue;
      for (var k = 0; k < sh.length; k += 2) {
        var cx = Math.floor((sh[k][0] - S.gridO.lon) / cell);
        var cy = Math.floor((sh[k][1] - S.gridO.lat) / cell);
        var key = cx + ',' + cy;
        (g[key] || (g[key] = [])).push([sh[k][0], sh[k][1], e.st, e.c]);
      }
    }
    S.grid = g;
  }
  function streetAt(lon, lat) {
    if (!S.grid) return null;
    var cell = S.gridCell, cx = Math.floor((lon - S.gridO.lon) / cell), cy = Math.floor((lat - S.gridO.lat) / cell);
    var best = null, bd = 1e9;
    for (var dx = -2; dx <= 2; dx++) for (var dy = -2; dy <= 2; dy++) {
      var arr = S.grid[(cx + dx) + ',' + (cy + dy)]; if (!arr) continue;
      for (var i = 0; i < arr.length; i++) {
        var dlon = (arr[i][0] - lon) * 111320 * Math.cos(lat * Math.PI / 180);
        var dlat = (arr[i][1] - lat) * 110540;
        var dd = dlon * dlon + dlat * dlat;
        if (dd < bd) { bd = dd; best = arr[i]; }
      }
    }
    return best && bd < 900 ? best : null;   // داخل ~30 م
  }

  /* ── النطاقات ── */
  function segBoxFor(seg) {
    var p = S.data.trace.p, n = p.length - 1;
    if (seg === 'all') return S.data.bbox;
    var a = seg === 'east' ? 0 : seg === 'mid' ? 1 : 2;
    var i0 = Math.floor(n * a / 3), i1 = Math.floor(n * (a + 1) / 3);
    var lo = [1e9, 1e9, -1e9, -1e9];
    for (var i = i0; i <= i1; i++) {
      lo[0] = Math.min(lo[0], p[i][1]); lo[1] = Math.min(lo[1], p[i][2]);
      lo[2] = Math.max(lo[2], p[i][1]); lo[3] = Math.max(lo[3], p[i][2]);
    }
    var pad = 0.0045;
    return [lo[0] - pad, lo[1] - pad, lo[2] + pad, lo[3] + pad];
  }
  function setSeg(seg) {
    S.seg = seg;
    S.segBox = segBoxFor(seg);
    fit(S.segBox);
    drawBase();
    extendPath(S.idx);
    var L = { all: 'الممر كامل', east: 'الثلث الشرقي', mid: 'الثلث الأوسط', west: 'الثلث الغربي' }[seg];
    var p = S.data.trace.p, i0 = 0, i1 = p.length - 1;
    if (seg !== 'all') {
      var a = { east: 0, mid: 1, west: 2 }[seg];
      i0 = Math.floor((p.length - 1) * a / 3); i1 = Math.floor((p.length - 1) * (a + 1) / 3);
    }
    $('#seg-sub').textContent = L + ' · من ' + hhmmss(S.data.trace.t0 + p[i0][0]) + ' إلى ' +
      hhmmss(S.data.trace.t0 + p[i1][0]) + ' · ' + fmt(distTo(i1) / 1000, 2) + ' كم تراكمية';
    $$('#segbar button').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-seg') === seg ? 'true' : 'false');
    });
  }

  /* ── الملء من البيانات ── */
  function fillHead() {
    var d = S.data;
    $('#chip-edges').textContent = d.edges.length.toLocaleString('en-US');
    var box = $('#kpi'); box.innerHTML = '';
    d.kpis.forEach(function (k) {
      var c = document.createElement('div'); c.className = 'c';
      c.innerHTML = '<b>' + k.value + '<i>' + k.unit + '</i></b><span>' + k.label + '</span>' +
        (k.foot ? '<small>' + k.foot + '</small>' : '');
      box.appendChild(c);
    });
    var gen = String(d.generated || '').replace('T', ' ').slice(0, 16);
    $('#src-note').textContent = 'المصدر: سجل الجلسة ' + gen + ' — يُولَّد بسكربت من سجل القياس وشبكة المحاكاة.';
    var tm = $('#trip-cards'); tm.innerHTML = '';
    d.kpis.forEach(function (k) {
      var c = document.createElement('div'); c.className = 'c';
      c.innerHTML = '<b>' + k.value + '<i>' + k.unit + '</i></b><span>' + k.label + '</span>' +
        (k.foot ? '<small>' + k.foot + '</small>' : '');
      tm.appendChild(c);
    });

    var p = d.trace.p, dur = (d.trace.t1 - d.trace.t0);
    var kv = $('#trip-kv'); kv.innerHTML = '';
    [['بداية الجلسة (محلي)', hhmmss(d.trace.t0)],
     ['نهاية الجلسة (محلي)', hhmmss(d.trace.t1)],
     ['المدة', Math.floor(dur / 3600) + ' س ' + Math.round((dur % 3600) / 60) + ' د'],
     ['نقاط المسار المسجّل', p.length.toLocaleString('en-US')],
     ['أعلى سرعة مسجّلة', fmt(Math.max.apply(null, p.map(function (x) { return x[3]; })), 1) + ' كم/س'],
     ['شارع الممر', d.corridor + ' · ' + fmt(d.corridor_km, 2) + ' كم'],
     ['مقاطع مقاسة على الممر', d.totals.stretches + ' مقطعًا متصلًا'],
     ['فجوات في السجل', d.totals.gaps]
    ].forEach(function (r) {
      var dt = document.createElement('dt'); dt.textContent = r[0];
      var dd = document.createElement('dd'); dd.textContent = r[1];
      kv.appendChild(dt); kv.appendChild(dd);
    });
  }

  /* ── التبويبات ── */
  function goto(view) {
    $$('.tabs button').forEach(function (b) {
      b.setAttribute('aria-selected', b.getAttribute('data-view') === view ? 'true' : 'false');
    });
    $$('.view').forEach(function (v) {
      v.classList.toggle('on', v.id === 'view-' + view);
    });
    if (view === 'map') { resize(); }
  }

  /* ── القياس ── */
  function resize() {
    var cv = $('#map');
    var rect = cv.getBoundingClientRect();
    if (!rect.width) return;
    S.W = rect.width; S.H = rect.height;
    cv.width = Math.round(S.W * S.dpr); cv.height = Math.round(S.H * S.dpr);
    if (S.data) { fit(S.segBox || S.data.bbox); drawBase(); extendPath(S.idx); }
  }

  /* ── الإقلاع ── */
  function boot() {
    Promise.all([
      fetch('data/anas.json').then(function (r) { return r.json(); }),
      fetch('data/junction.json').then(function (r) { return r.json(); }).catch(function () { return null; })
    ]).then(function (res) {
      S.data = res[0]; S.junc = res[1];
      fillHead(); buildIndex(); buildCum();
      S.vt = 0; S.idx = 0;
      var m = /[#&]t=(\d+)/.exec(location.hash);
      if (m) {
        var want = +m[1], tr0 = S.data.trace.p;
        for (var z = 0; z < tr0.length; z++) { if (tr0[z][0] >= want) { S.idx = z; break; } }
        S.vt = tr0[S.idx][0];
      }
      resize(); setSeg('all'); extendPath(S.idx);
      requestAnimationFrame(frame); requestAnimationFrame(tick);

      $('#play').onclick = function () {
        if (S.playing) { stop(); return; }
        if (S.idx >= S.data.trace.p.length - 1) { S.idx = 0; S.vt = 0; resetPath(); }
        play();
      };
      $('#speed').onchange = function (e) { S.mult = +e.target.value; };
      $('#segbar').onclick = function (e) {
        var b = e.target.closest('button'); if (b) setSeg(b.getAttribute('data-seg'));
      };
      ['ly-net', 'ly-corr', 'ly-junc'].forEach(function (id) {
        $('#' + id).onchange = function () { drawBase(); extendPath(S.idx); };
      });
      $('#ly-path').onchange = function () { };
      $('#track').onmousedown = function (e) {
        var r = e.currentTarget.getBoundingClientRect();
        var f = 1 - (e.clientX - r.left) / r.width;
        f = Math.min(1, Math.max(0, f));
        var n = S.data.trace.p.length - 1;
        S.idx = Math.round(f * n); S.vt = S.data.trace.p[S.idx][0];
        resetPath(); extendPath(S.idx);
      };
      $$('[data-goto]').forEach(function (b) {
        b.onclick = function () { goto(b.getAttribute('data-goto')); };
      });
      $$('.tabs button').forEach(function (b) {
        b.onclick = function () { goto(b.getAttribute('data-view')); };
      });

      // تسمية الشارع تحت المؤشر
      var tip = $('#tip');
      $('#map').onmousemove = function (e) {
        var r = e.currentTarget.getBoundingClientRect();
        var lon = S.lon0 + ((e.clientX - r.left) - S.tx) / S.scale / (111320 * Math.cos(S.lat0 * Math.PI / 180));
        var lat = S.lat0 - ((e.clientY - r.top) - S.ty) / S.scale / 110540;
        var hit = streetAt(lon, lat);
        if (hit) {
          tip.textContent = hit[2] + (hit[3] ? ' · ممر أنس' : '');
          tip.style.left = (e.clientX - r.left + 14) + 'px';
          tip.style.top = (e.clientY - r.top - 10) + 'px';
          tip.style.opacity = 1;
        } else tip.style.opacity = 0;
      };
      $('#map').onmouseleave = function () { tip.style.opacity = 0; };

      window.addEventListener('resize', resize);
      var box = $('#view-map'); if (box && window.ResizeObserver) new ResizeObserver(resize).observe(box);
      var mv = /[#&]v=(\w+)/.exec(location.hash);
      goto(mv ? mv[1] : 'map');
    }).catch(function (err) {
      document.title = 'فشل تحميل البيانات: ' + err.message;
      console.error(err);
    });
  }

  function clock() {
    var d = new Date(), p = function (n) { return (n < 10 ? '0' : '') + n; };
    var s = new Date(d.getTime() + (TZ * 1000) + (d.getTimezoneOffset() * 60000));
    $('#clock').textContent = p(s.getHours()) + ':' + p(s.getMinutes()) + ':' + p(s.getSeconds());
    setTimeout(clock, 1000);
  }

  document.addEventListener('DOMContentLoaded', function () { clock(); boot(); });
})();
