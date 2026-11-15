(function () {
  'use strict';

  var get = function (id) { return document.getElementById(id); };
  var number = new Intl.NumberFormat('en', { maximumFractionDigits: 2 });
  var scenarios = [
    { key: 'baseline', label: 'الوضع المرجعي' },
    { key: 'closure', label: 'إغلاق التقاطع' },
    { key: 'detour', label: 'الإغلاق مع تحويلة مدعومة' }
  ];

  function read(path) {
    return fetch(path).then(function (response) {
      if (!response.ok) throw new Error(path);
      return response.json();
    });
  }

  function renderComparison(results) {
    var minutes = results.trips_mean_min;
    var steps = 4;
    var axisMax = Math.ceil(Math.max.apply(null, scenarios.map(function (s) {
      return minutes[s.key];
    })) / 10) * 10;

    for (var i = 0; i <= steps; i++) {
      var mark = document.createElement('span');
      mark.textContent = number.format(axisMax * i / steps);
      get('scenario-axis').appendChild(mark);
    }

    function showImpact(key) {
      var panel = get('scenario-impact');
      var street = results.damage[key] && results.damage[key].top_streets[0];

      panel.replaceChildren();
      if (!street) {
        panel.textContent = 'الوضع المرجعي هو نقطة المقارنة لقياس تغيّر زمن الرحلة والتأخير على الطرق المجاورة.';
        return;
      }

      var title = document.createElement('strong');
      title.textContent = 'أكبر زيادة في التأخير على ' + street.street;
      var value = document.createElement('span');
      value.textContent = number.format(street.added_vh) + ' مركبة-ساعة تأخير مضاف مقارنة بالوضع المرجعي';
      panel.append(title, value);
    }

    scenarios.forEach(function (scenario) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'scenario-row ' + scenario.key;
      button.setAttribute('aria-pressed', 'false');

      var caption = document.createElement('span');
      caption.className = 'scenario-caption';
      var label = document.createElement('span');
      label.textContent = scenario.label;
      var value = document.createElement('strong');
      value.textContent = number.format(minutes[scenario.key]) + ' دقيقة';
      caption.append(label, value);

      var rail = document.createElement('span');
      rail.className = 'scenario-rail';
      rail.setAttribute('aria-hidden', 'true');
      var fill = document.createElement('span');
      fill.style.width = (minutes[scenario.key] / axisMax * 100) + '%';
      rail.appendChild(fill);
      button.append(caption, rail);
      button.addEventListener('click', function () {
        get('scenario-rows').querySelectorAll('button').forEach(function (row) {
          row.setAttribute('aria-pressed', row === button ? 'true' : 'false');
        });
        showImpact(scenario.key);
      });
      get('scenario-rows').appendChild(button);
    });

    get('scenario-note').textContent = 'متوسط زمن الرحلات داخل شبكة المحاكاة عبر ' +
      number.format(results.policy.seeds.length) +
      ' تشغيلات. تُستخدم القيم لمقارنة البدائل داخل النموذج. المعايرة الميدانية لزمن الرحلة في التقاطع قيد الاستكمال.';
    get('scenario-status').hidden = true;
    get('scenario-comparison').hidden = false;
    get('scenario-rows').querySelector('.closure').click();
  }

  read('data/ai_facts.json').then(renderComparison).catch(function () {
    get('scenario-status').textContent = 'تعذّر تحميل نتائج المقارنة.';
  });

  read('data/validation.json').then(function (data) {
    get('decision-points').textContent = number.format(data.session.points) + ' نقطة GPS من جولة ميدانية واحدة';
    get('decision-coverage').textContent = number.format(data.totals.field_m / 1000) +
      ' كم من الجولة دخلت المطابقة بشبكة الطرق';
    get('decision-proof').hidden = false;
  }).catch(function () {});
})();
