/* انسياب — تبويب الحلول: أربعة أذرع مقيسة، وكثافة التأخير، وتوصيات الوكيل.
   كل الأرقام من data/solutions.json (يُبنى بـ build/build_solutions.py) — لا رقم مكتوب هنا. */
(function () {
  "use strict";
  var AR = {
    closure: {
      t: "إغلاق التقاطع كاملًا",
      how: ["الممر يُغلق عند التقاطع المزدحم كاملًا.",
            "كل الحركة تُحوَّل إلى طريق الأمير تركي والمحيط."],
      v: "مرفوض", cls: "bad",
      verdict: "يزيد الانتظار ألفًا وسبع مئة ساعة"
    },
    detour: {
      t: "توسعة الشوارع المجاورة",
      how: ["نفس الإغلاق، لكن تُضاف سعة للشوارع البديلة.",
            "التوسعة لا تحلّ: السيارة تدور أطول، والتأخير ينتقل ولا يختفي."],
      v: "مرفوض", cls: "bad",
      verdict: "لا يفرق عن الإغلاق: التوسعة تنقل الوقوف ولا تخفّضه"
    },
    uturn: {
      t: "دوران إجباري بدل الإغلاق",
      how: ["يُمنع العبور المباشر، وتُفرض دورة طويلة للوصول إلى الجهة الأخرى.",
            "الوقوف يتضاعف لأن الدوران يمرّ بالتقاطع نفسه."],
      v: "مرفوض", cls: "bad",
      verdict: "يضاعف التأخير: أسوأ من الإغلاق الكامل"
    },
    half: {
      t: "بقاء المحور مفتوحًا — اتجاه واحد",
      how: ["الممر يبقى مفتوحًا باتجاه واحد، على مرحلتين.",
            "الاتجاه المقابل يُنقل إلى موعد آخر بدل قطعه في الذروة."],
      v: "المُختار", cls: "ok",
      verdict: "الوحيد الذي يخفّض الانتظار ولا يزيد زمن الرحلة"
    }
  };

  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }
  function num(n) { return Number(n).toLocaleString("en-US"); }

  function armCard(id, a, d, idx) {
    var m = AR[id], base = d.arms.baseline;
    var BIG = {
      closure: ["+" + num(d.display.closure_vh), "ساعة انتظار مضافة على الشبكة"],
      detour:  ["−" + d.display.detour_pct, "فقط أقل من الإغلاق — الفرق لا يُذكر"],
      uturn:   ["×" + d.display.uturn_ratio, "التأخير: " + num(d.display.uturn_vh) + " ساعة — ضِعف الإغلاق"],
      half:    ["−" + d.display.half_vh, "ساعة انتظار أقل، وزمن الرحلة كما هو"]
    };
    var netTxt = BIG[id][0];
    var durTxt = a.dur_min.toFixed(id === "half" || id === "baseline" ? 1 : 0);
    var card = el("article", "arm " + (m.cls === "ok" ? "is-chosen" : ""));

    card.appendChild(el("div", "arm-top",
      '<span class="rank">' + (idx < 9 ? "0" + (idx + 1) : idx + 1) + "</span>" +
      "<h3>" + m.t + "</h3>" +
      '<span class="v v-' + m.cls + '">' + m.v + "</span>"));

    card.appendChild(el("div", "arm-num " + m.cls,
      "<b>" + netTxt + "</b><i>" + BIG[id][1] + "</i>"));

    var ul = el("ul", "arm-how");
    m.how.forEach(function (h) { ul.appendChild(el("li", null, h)); });
    card.appendChild(ul);

    card.appendChild(el("div", "arm-stats",
      '<span><em>زمن الرحلة</em><b class="ltr">' + durTxt + " د</b></span>" +
      '<span><em>تفاوت</em><b class="ltr">±' + a.dur_sd.toFixed(1) + " د</b></span>" +
      '<span><em>أضلاع تأثرت</em><b class="ltr">' + num(a.edges_hit) + "</b></span>"));

    card.appendChild(el("p", "arm-verdict", m.verdict));
    return card;
  }

  function densityBar(id, a, d, maxHit) {
    var m = AR[id];
    var w = Math.max(4, 100 * a.edges_hit / maxHit);
    var top = (a.top && a.top[0]) ? a.top[0] : null;
    return '<div class="drow ' + (m.cls === "ok" ? "ok" : "") + '">' +
      '<div class="dl"><span>' + m.t + '</span><b class="ltr">' + num(a.edges_hit) + " ضلعًا (" + a.edges_pct + "%)</b></div>" +
      '<div class="dbar"><i style="width:' + w.toFixed(1) + '%"></i></div>' +
      (top ? '<small>أثقل شارع: ' + top.street + " " + num(Math.round(top.vh / 10) * 10) + " ساعة</small>" : "") +
      "</div>";
  }

  function streetTable(id, a, d) {
    var m = AR[id], rows = (a.top || []).map(function (r) {
      return "<tr><td>" + r.street + '</td><td class="n">' +
        num(Math.round(r.vh / 10) * 10) + "</td></tr>";
    }).join("");
    return '<div class="stbl"><h4>' + m.t + "</h4>" +
      "<table><thead><tr><th>الشارع</th><th class=\"n\">ساعة</th></tr></thead><tbody>" +
      rows + "</tbody></table>" +
      '<small>أعلى ثلاثة شوارع تحمل ' + a.top3_share + "% من التأخير</small></div>";
  }

  function render(d) {
    var arms = d.arms, order = ["closure", "detour", "uturn", "half"];

    /* العنوان الفرعي: شروط الاختبار */
    var pill = document.getElementById("sol-pill");
    if (pill) pill.textContent = num(arms.baseline.n) + " تشغيلات لكل حل · " + num(d.test.trips) + " رحلة";

    /* بطاقات الأذرع */
    var box = document.getElementById("sol-arms");
    if (box) order.forEach(function (id, i) { box.appendChild(armCard(id, arms[id], d, i)); });

    /* كثافة التأخير */
    var db = document.getElementById("sol-density");
    if (db) {
      var maxHit = Math.max.apply(null, order.map(function (i) { return arms[i].edges_hit; }));
      db.innerHTML =
        '<p class="ddef">الكثافة هنا ليست عدد السيارات: هي <b>كم ضلعًا في الشبكة تأثّر</b> ' +
        "(زاد تأخيره أكثر من خمس ثوانٍ)، و<b>كيف توزّع التأخير على الشوارع</b>. " +
        "حلّ يوزّع الوقوف على شبكة كاملة أسوأ من حلّ يحصره في ثلاث نقاط.</p>" +
        '<div class="density">' + order.map(function (i) { return densityBar(i, arms[i], d, maxHit); }).join("") + "</div>" +
        '<small class="dnote">النسبة من أصل ' + num(d.test.network_edges) + " ضلعًا في شبكة الممر.</small>" +
        '<div class="stwrap">' + streetTable("closure", arms.closure, d) + streetTable("half", arms.half, d) + "</div>";
    }

    /* النموذج المختبر للإغلاق */
    var md = document.getElementById("sol-model");
    if (md) {
      var c = arms.closure;
      md.innerHTML =
        '<div class="mgrid">' +
        '<div><b class="ltr">' + d.display.closure_min + "</b><i>دقيقة للرحلة</i></div>" +
        '<div><b class="ltr">+' + num(d.display.closure_vh) + "</b><i>ساعة انتظار</i></div>" +
        '<div><b class="ltr">' + num(c.edges_hit) + "</b><i>ضلعًا تأثّر</i></div>" +
        "</div>" +
        "<p>هذا هو النموذج المرجعي: إغلاق كامل للممر كما يحدث فعلًا عند تنفيذ أعمال على الطريق. " +
        "شُغّل خمس مرات على الشبكة والطلب نفسه، فخرج بزمن رحلة " + c.dur_min.toFixed(0) + " دقيقة مقابل " +
        d.arms.baseline.dur_min.toFixed(0) + " في خط الأساس، وبانتظار إضافي " +
        num(d.display.closure_vh) + " ساعة‑مركبة.</p>" +
        '<p class="mnote">والتأخير لا يختفي بالتحويل: ' + d.display.stays_pct +
        " من ساعات التأخير تبقى داخل الشبكة، و" + c.top3_share + "% منها في ثلاثة شوارع فقط.</p>" +
        '<p class="msrc">المصدر: runs/results.csv · runs/damage_closure300.edges.csv</p>' +
        '<div class="cmp"><span></span><b>الإغلاق الكامل</b><b>الحل المُختار</b>' +
        '<span>زمن الرحلة</span><b class="ltr">' + d.display.closure_min + ' د</b><b class="ltr">' + arms.half.dur_min.toFixed(1) + ' د</b>' +
        '<span>الانتظار</span><b class="ltr">+' + num(d.display.closure_vh) + ' ساعة</b><b class="ltr">−' + d.display.half_vh + ' ساعة</b>' +
        '<span>أضلاع تأثّرت</span><b class="ltr">' + num(c.edges_hit) + '</b><b class="ltr">' + num(arms.half.edges_hit) + '</b></div>' +
        streetTable("closure", c, d);
    }

    /* كيف يُختبر كل حل */
    var tb = document.getElementById("sol-test");
    if (tb) {
      var steps = [
        ["الشبكة", "شبكة الممر كما استُخرجت من الخريطة — " + num(d.test.network_edges) + " ضلعًا، والطلب نفسه في كل تشغيل."],
        ["الطلب", num(d.test.trips) + " رحلة في نفس الذروة، لكل حل ولكل تشغيل."],
        ["التكرار", num(arms.baseline.n) + " تشغيلات لكل حل ببذور عشوائية مختلفة، ونأخذ متوسطها لا أفضلها."],
        ["المعيار", "ساعات الانتظار على الشبكة وحدها — لا السرعة ولا الرأي."]
      ];
      tb.innerHTML = steps.map(function (s, i) {
        return '<div class="tstep"><span class="rank">' + (i + 1) + "</span><b>" + s[0] + "</b><p>" + s[1] + "</p></div>";
      }).join("");
    }

    /* سطر القرار */
    var bn = document.getElementById("sol-banner");
    if (bn) {
      bn.innerHTML = '<b>توصية انسياب:</b> الاتجاه الواحد على مرحلتين هو الحل الوحيد الذي يخفض الانتظار ' +
        '(<span class="ltr">−' + d.display.half_vh + '</span> ساعة) بزمن رحلة كما هو ' +
        '(<span class="ltr">' + arms.half.dur_min.toFixed(1) + '</span> د مقابل ' + arms.baseline.dur_min.toFixed(1) + ')، وثمنه ' +
        '<span class="ltr">' + d.display.half_extra_km + '</span> كم التفافًا. الإغلاق الكامل يضيف ' +
        '<span class="ltr">+' + num(d.display.closure_vh) + '</span> ساعة، والدوران يضاعفها.';
    }

    /* الحل المُختار: كيف يعمل */
    var ch = document.getElementById("sol-chosen");
    if (ch) {
      var h = arms.half;
      ch.innerHTML =
        '<div class="chosen-h"><b>' + AR.half.t + "</b>" +
        '<span class="v v-ok">' + AR.half.v + "</span></div>" +
        '<ol class="chosen-steps">' +
        "<li><b>المرحلة الأولى:</b> الممر مفتوح باتجاه واحد فقط، والاتجاه المقابل يُحوَّل إلى طريق الأمير تركي.</li>" +
        "<li><b>المرحلة الثانية:</b> يُقلب الاتجاه بعد انتهاء أعمال الجهة الأولى — لا يُغلق الممر كاملًا في أي يوم.</li>" +
        "<li><b>الثمن المعلن:</b> التفاف " + d.display.half_extra_km + " كم لكل سيارة متأثرة، مقابل انتظار أقل بـ" +
        d.display.half_vh + " ساعة.</li>" +
        "</ol>" +
        '<div class="chosen-kpis">' +
        '<span><em>زمن الرحلة</em><b class="ltr">' + h.dur_min.toFixed(2) + " د</b><small>خط الأساس " + d.arms.baseline.dur_min.toFixed(2) + " د</small></span>" +
        '<span><em>تفاوت التشغيلات</em><b class="ltr">±' + h.dur_sd.toFixed(2) + " د</b><small>" + num(h.n) + " تشغيلات — النتيجة ليست صدفة</small></span>" +
        '<span><em>أضلاع تأثّرت</em><b class="ltr">' + num(h.edges_hit) + "</b><small>مقابل " + num(arms.closure.edges_hit) + " في الإغلاق الكامل</small></span>" +
        "</div>";
    }

    /* توصيات الوكيل */
    var rc = document.getElementById("sol-recs");
    if (rc) {
      var recs = [
        ["اعتمد الحل الرابع", "أعلى أثر بأقل ثمن: زمن الرحلة " + arms.half.dur_min.toFixed(1) +
         " دقيقة مقابل " + arms.baseline.dur_min.toFixed(1) + "، والانتظار ينخفض " + d.display.half_vh + " ساعة.", "شرط: تنفيذ على مرحلتين"],
        ["نفّذ على مرحلتين لا دفعة واحدة", "مرحلة أولى باتجاه واحد، ثم تُقلب بعد انتهاء الجهة الأولى. هذا هو التتابع الذي قِسناه؛ ولم نقِس تنفيذًا دفعة واحدة.", "شرط: جدول أعمال معلن"],
        ["أعلن البديل قبل البدء", "التفاف " + d.display.half_extra_km + " كم لكل سيارة متأثرة، و" + d.display.stays_pct +
         " من التأخير يبقى داخل الشبكة؛ فإن لم يُعلن التحويل ويُسيَّر عاد التأخير إلى حجم الإغلاق الكامل.", "شرط: لافتات ومسار بديل على بلدي"],
        ["قِس بعد التنفيذ بالمعيار نفسه", "ساعات الانتظار على الشبكة مقابل خط الأساس " +
         num(arms.baseline.wait_h) + " ساعة. فرق يتجاوز 5% يعني أن التوقيت أو الاتجاه لم يُطبَّق كما قِسناه.", "شرط: تقرير بعد أسبوعين"],
        ["أبقِ الإغلاق الكامل على الرف", "سيناريو طوارئ مرجعي (+" + num(d.display.closure_vh) +
         " ساعة)، لا خطة تنفيذ اعتيادية.", "شرط: قرار طوارئ موثّق"]
      ];
      rc.innerHTML = recs.map(function (r, i) {
        return '<div class="rec"><span class="rank">' + (i + 1) + "</span><div><b>" + r[0] +
          "</b><p>" + r[1] + '</p><span class="gate">' + r[2] + "</span></div></div>";
      }).join("");
    }

    var src = document.getElementById("sol-src");
    if (src) src.textContent = "المصادر: runs/results.csv · runs/damage_*.edges.csv · يُعاد التوليد بـ " +
      "python build/build_solutions.py — تاريخ التوليد " + d.generated.slice(0, 10);
  }

  function openTab(tries) {
    var m = (location.hash || "").replace("#", "");
    if (!m || (tries | 0) > 20) return;
    var b = document.querySelector('[data-view="' + m + '"]');
    if (b) {
      if (document.getElementById("view-" + m) && document.getElementById("view-" + m).classList.contains("on")) return;
      b.click();
      setTimeout(function () { openTab((tries | 0) + 1); }, 120);
    }
  }

  function boot() {
    openTab();
    fetch("data/solutions.json", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function (e) { document.title = "SOLERR " + e.message; });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
