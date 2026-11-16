/* view-validation — كل رقم هنا من data/validation.json (ناتج build/build_validation.py).
   لا رقم مكتوب بيد في هذا الملف؛ البوابة build/verify_validation.py تفحص ذلك. */
(function () {
  "use strict";

  var fmt = function (n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); };

  /* أي عنصر [data-goto] يفتح تبويباً عبر نفس أزرار الشريط (لا منطق تبويب مكرَّر هنا) */
  document.addEventListener("click", function (ev) {
    var t = ev.target.closest("[data-goto]");
    if (!t) return;
    ev.preventDefault();
    var btn = document.querySelector('.tabs button[data-view="' + t.getAttribute("data-goto") + '"]');
    if (btn) btn.click();
  });

  function kpiCard(k) {
    var d = document.createElement("div");
    d.className = "card kpi ok";
    d.innerHTML =
      '<div class="lab">' + k.label + "</div>" +
      '<div class="val">' + k.value + "<span> " + k.unit + "</span></div>" +
      '<div class="sub">' + k.foot + "</div>";
    return d;
  }

  function table(cols, rows, cls) {
    var t = document.createElement("table");
    t.className = "vtab";
    var th = "<thead><tr>" + cols.map(function (c) { return "<th>" + c + "</th>"; }).join("") + "</tr></thead>";
    var tb = "<tbody>" + rows.map(function (r) {
      return "<tr>" + r.map(function (c, i) {
        return "<td" + (i ? ' class="n"' : "") + ">" + c + "</td>";
      }).join("") + "</tr>";
    }).join("") + "</tbody>";
    t.innerHTML = th + tb;
    return t;
  }

  fetch("data/validation.json", { cache: "no-store" })
    .then(function (r) { return r.json(); })
    .then(function (v) {
      var s = v.session;

      var LRI = "\u2066", PDI = "\u2069";
      document.getElementById("v-lead").textContent =
        s.rate_hz + " هرتز · " + fmt(s.points) + " نقطة · " +
        (s.window_local ? LRI + s.window_local[0] + PDI + " ← " + LRI + s.window_local[1] + PDI + " (توقيت الرياض) · " : "") +
        LRI + s.window_utc[0] + PDI + " ← " + LRI + s.window_utc[1] + PDI + " (UTC) · " +
        s.vehicle + " · " + s.logger + " · " + LRI + s.firmware + PDI;

      var box = document.getElementById("v-kpis");
      v.kpis.forEach(function (k) { box.appendChild(kpiCard(k)); });

      var vid = document.getElementById("v-video-body");
      vid.innerHTML =
        '<video controls preload="metadata" poster="' + v.video.poster + '" width="100%">' +
        '<source src="' + v.video.src + '" type="video/mp4"></video>' +
        '<p class="note" style="margin:10px 0 0">' + v.video.seconds + " ثانية · سرعة ×" +
        v.video.speedup + " · " + fmt(v.video.bytes) + " بايت · <span class=\"mono\">sha256 " +
        v.video.sha16 + "…</span> · الأثر الأخضر مقيس، الأزرق وقوف، الكهرماني سرعة عالية</p>";

      var lim = document.getElementById("v-limits");
      v.limits.forEach(function (t) {
        var li = document.createElement("li");
        li.textContent = t;
        lim.appendChild(li);
      });

      var tt = v.totals;
      document.getElementById("v-totals").textContent =
        "المجموع على المقاطع المتصلة: ميدان " + fmt(tt.field_m) + " م مقابل شبكة " + fmt(tt.net_m) +
        " م على المسار نفسه (خطأ تراكمي " + tt.agg_err_pct + "%).";

      document.getElementById("v-table").appendChild(table(
        ["المقطع (الرياض)", "نقاط", "ميدان م", "شبكة م", "خطأ %", "كم/س"],
        v.stretches.map(function (r) {
          return [r.t0 + "–" + r.t1, r.pts, r.field_m, r.net_m, r.err, r.kmh];
        })
      ));

      document.getElementById("v-evidence").appendChild(table(
        ["الملف", "بايت", "sha256", "ماذا يثبت"],
        v.evidence.map(function (e) {
          return ['<span class="mono">' + e.file + "</span>",
                  e.bytes ? fmt(e.bytes) : "—",
                  e.sha16 ? '<span class="mono">' + e.sha16 + "…</span>" : "—",
                  e.what];
        })
      ));

      document.getElementById("v-source").textContent = v.source + " · تحقق " + v.as_of;
      document.getElementById("view-validation").setAttribute("data-ready", "1");
    })
    .catch(function (err) {
      document.getElementById("v-lead").textContent = "تعذّر تحميل بيانات التحقق: " + err.message;
    });
})();
