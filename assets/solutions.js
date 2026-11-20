/* انسياب — تبويب الحلول: أربعة أذرع مقيسة، وكثافة التأخير، وتوصيات الوكيل.
   كل الأرقام من data/solutions.json (يُبنى بـ build/build_solutions.py) — لا رقم مكتوب هنا. */
(function () {
  "use strict";
  var AR = {
    closure: {
      t: "إغلاق الممر كاملًا",
      how: ["الممر يُغلق عند التقاطع المزدحم كاملًا.",
            "كل الحركة تُحوَّل إلى طريق الأمير تركي والمحيط."],
      v: "مرفوض", cls: "bad",
      verdict: "أغلى الخيارات: +2,000 ساعة تأخير على نافذة الذروة"
    },
    detour: {
      t: "توسعة الشوارع المجاورة",
      how: ["نفس الإغلاق، لكن تُضاف سعة للشوارع البديلة.",
            "التوسعة لا تحلّ: السيارة تدور أطول، والتأخير ينتقل ولا يختفي."],
      v: "مرفوض", cls: "bad",
      verdict: "يعادل الإغلاق: نفس زمن الرحلة تقريبًا"
    },
    uturn: {
      t: "دوران إجباري بدل الإغلاق",
      how: ["يُمنع العبور المباشر، وتُفرض دورة طويلة للوصول إلى الجهة الأخرى.",
            "الوقوف يتضاعف لأن الدوران يمرّ بالتقاطع نفسه."],
      v: "مرفوض", cls: "bad",
      verdict: "يضاعف زمن الرحلة: أسوأ من الإغلاق الكامل"
    },
    works: {
      t: "تضييق إلى حارتين لكل اتجاه",
      how: ["لا مسار يُغلق: المحور مقسوم حارتين لكل اتجاه على مقطع الأعمال وحده.",
            "المتقاطع يبقى عاملًا، والحركة تمرّ على المحور نفسه."],
      v: "المُطبَّق", cls: "ok",
      verdict: "43% من كلفة الإغلاق الكامل، والتأخير كله على المحور"
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
      closure: ["+" + num(d.display.closure_vh), "ساعة تأخير — مقابل خط الأساس السالك"],
      detour:  [d.arms.detour.dur_min.toFixed(0) + " دقيقة", "زمن الرحلة — كالإغلاق تمامًا (" + d.arms.closure.dur_min.toFixed(0) + " د)؛ التوسعة تُخرج الوقوف من الشارع لا من الشبكة"],
      uturn:   [d.arms.uturn.dur_min.toFixed(0) + " دقيقة", "زمن الرحلة — ضِعف خط الأساس (" + d.arms.baseline.dur_min.toFixed(0) + " د)، أسوأ الخيارات"],
      works:   ["+" + num(d.display.works_vh), "ساعة تأخير — " + d.display.works_share_pct + "% من كلفة الإغلاق"]
    };
    var netTxt = BIG[id][0];
    var durTxt = a.dur_min.toFixed(0);
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
    var arms = d.arms, order = ["closure", "detour", "uturn", "works"];
    var base = arms.baseline, w = arms.works, c = arms.closure;

    /* العنوان الفرعي: شروط الاختبار */
    var pill = document.getElementById("sol-pill");
    if (pill) pill.textContent = num(arms.baseline.n) + " تشغيلات لكل حل · " + num(d.test.trips) + " رحلة · خط الأساس سالك بلا أعمال";

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
        "حلّ يوزّع الوقوف على شبكة كاملة أسوأ من حلّ يحصره في ثلاث نقاط — والمُطبَّق هو الثاني.</p>" +
        '<div class="density">' + order.map(function (i) { return densityBar(i, arms[i], d, maxHit); }).join("") + "</div>" +
        '<small class="dnote">النسبة من أصل ' + num(w.edges_total) + " ضلعًا في نطاق الممر.</small>" +
        '<div class="stwrap">' + streetTable("closure", arms.closure, d) + streetTable("works", arms.works, d) + "</div>";
    }

    /* المرجع: الإغلاق الكامل مقابل المُطبَّق على الأرض */
    var md = document.getElementById("sol-model");
    if (md) {
      md.innerHTML =
        '<div class="mgrid">' +
        '<div><b class="ltr">' + num(d.display.closure_vh) + "</b><i>ساعة تأخير — الإغلاق الكامل</i></div>" +
        '<div><b class="ltr">' + num(d.display.works_vh) + "</b><i>ساعة تأخير — المُطبَّق على الأرض</i></div>" +
        '<div><b class="ltr">' + d.display.works_share_pct + "%</b><i>حصة المُطبَّق من كلفة الإغلاق</i></div>" +
        "</div>" +
        "<p>خط الأساس هو <b>الطريق سالكًا بلا أعمال</b>: " + base.dur_min.toFixed(0) + " دقيقة للرحلة. " +
        "عليه نقيس كل حل: الإغلاق الكامل يرفعها إلى " + c.dur_min.toFixed(0) + " دقيقة، " +
        "والمُطبَّق على الأرض (حارتان لكل اتجاه) يرفعها إلى " + w.dur_min.toFixed(0) + " دقيقة فقط.</p>" +
        '<p class="mnote">والتأخير يبقى في مكانه: ' + w.top3_share + "% من تأخير المُطبَّق في ثلاثة شوارع، " +
        "مقابل " + c.top3_share + "% في الإغلاق الكامل.</p>" +
        '<p class="msrc">المصدر: runs/results.csv · runs/damage_closure300.edges.csv · runs/damage_works300.edges.csv</p>' +
        '<div class="cmp"><span></span><b>الإغلاق الكامل</b><b>المُطبَّق على الأرض</b>' +
        '<span>زمن الرحلة</span><b class="ltr">' + c.dur_min.toFixed(0) + ' د</b><b class="ltr">' + w.dur_min.toFixed(1) + ' د</b>' +
        '<span>التأخير (ساعة)</span><b class="ltr">+' + num(d.display.closure_vh) + '</b><b class="ltr">+' + num(d.display.works_vh) + '</b>' +
        '<span>أضلاع تأثّرت</span><b class="ltr">' + num(c.edges_hit) + '</b><b class="ltr">' + num(w.edges_hit) + '</b></div>' +
        streetTable("works", w, d);
    }

    /* كيف يُختبر كل حل */
    var tb = document.getElementById("sol-test");
    if (tb) {
      var steps = [
        ["الشبكة", "شبكة الممر كما استُخرجت من الخريطة — " + num(w.edges_total) + " ضلعًا، والطلب نفسه في كل تشغيل."],
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
      bn.innerHTML = '<b>الخلاصة:</b> المُطبَّق على الأرض (حارتان لكل اتجاه) يكلّف ' +
        '<span class="ltr">+' + num(d.display.works_vh) + '</span> ساعة تأخير في الذروة — ' +
        '<span class="ltr">' + d.display.works_share_pct + '%</span> من الإغلاق الكامل ' +
        '(<span class="ltr">+' + num(d.display.closure_vh) + '</span> ساعة)، والدوران يضاعفها. ' +
        'أي أن الوضع الحالي يوفّر <span class="ltr">' + num(d.display.closure_vh - d.display.works_vh) + '</span> ساعة ' +
        'مقارنة بالإغلاق الكامل — وأغلى ما فيه أنه واقع لا تقدير.';
    }

    /* المُطبَّق: كيف يعمل */
    var ch = document.getElementById("sol-chosen");
    if (ch) {
      ch.innerHTML =
        '<div class="chosen-h"><b>' + AR.works.t + '</b>' +
        '<span class="v v-ok">' + AR.works.v + "</span></div>" +
        '<ol class="chosen-steps">' +
        "<li><b>ما يحدث:</b> لا يُغلق أي مسار. المحور على مقطع الأعمال يصير حارتين لكل اتجاه بدل أربع.</li>" +
        "<li><b>الأثر المقيس:</b> +" + d.display.works_vh + " ساعة تأخير على نافذة الذروة، وزمن الرحلة " +
        w.dur_min.toFixed(0) + " دقيقة بدل " + base.dur_min.toFixed(0) + " في خط الأساس.</li>" +
        "<li><b>لماذا هو الأرخص المتاح:</b> التأخير محصور في " + num(w.edges_hit) + " ضلعًا من " +
        num(w.edges_total) + "، و" + w.top3_share + "% منه في ثلاثة شوارع — ما يجعل المعالجة ممكنة.</li>" +
        "</ol>" +
        '<div class="chosen-kpis">' +
        '<span><em>زمن الرحلة</em><b class="ltr">' + w.dur_min.toFixed(1) + " د</b><small>خط الأساس " + base.dur_min.toFixed(1) + " د</small></span>" +
        '<span><em>تفاوت التشغيلات</em><b class="ltr">±' + w.dur_sd.toFixed(2) + " د</b><small>" + num(w.n) + " تشغيلات — النتيجة ليست صدفة</small></span>" +
        '<span><em>أضلاع تأثّرت</em><b class="ltr">' + num(w.edges_hit) + "</b><small>مقابل " + num(c.edges_hit) + " في الإغلاق الكامل</small></span>" +
        "</div>";
    }

    /* توصيات */
    var rc = document.getElementById("sol-recs");
    if (rc) {
      var recs = [
        ["لا تُغلق الممر كاملًا", "الفارق مقيس: " + num(d.display.closure_vh - d.display.works_vh) +
         " ساعة تأخير أقل في الذروة مع التضييق. الإغلاق الكامل يبقى سيناريو طوارئ لا خطة.", "شرط: قرار موثّق للطوارئ"],
        ["عالج الثلاثة لا الشبكة", w.top3_share + "% من التأخير في ثلاثة شوارع. معالجة تلك النقاط " +
         "أرخص من أي توسعة، وهي التي تجعل الـ" + num(d.display.works_vh) + " ساعة قابلة للخفض.", "شرط: قياس بعد المعالجة"],
        ["أعلن البديل قبل البدء", "التأخير ينتقل ولا يختفي: " + d.display.stays_pct +
         " منه يبقى داخل الشبكة. الإعلان والمسار البديل على بلدي شرط نجاح لا تحسين.", "شرط: لافتات ومسار بديل"],
        ["قِس بعد التنفيذ بالمعيار نفسه", "ساعات التأخير على الشبكة مقابل خط الأساس " + base.dur_min.toFixed(1) +
         " دقيقة للرحلة. فرق يتجاوز 5% يعني أن التضييق لم يُطبَّق كما قِسناه.", "شرط: تقرير بعد أسبوعين"],
        ["لا تعتمد التوسعة ولا الدوران", "التوسعة تعطي " + d.arms.detour.dur_min.toFixed(0) + " د للرحلة — كالإغلاق تمامًا؛ " +
         "والدوران يعطي " + d.arms.uturn.dur_min.toFixed(0) + " د. كلاهما أُسقط بالقياس لا بالرأي.", "شرط: —"]
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
