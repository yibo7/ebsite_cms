/* ===================================================================
   Green Rich 金瑞治 — 首页 JavaScript
   =================================================================== */

// ===== Hero 轮播 =====
(function() {
  const slides = document.querySelectorAll('.hero-slide');
  const indicators = document.querySelectorAll('.hero-indicator');
  let current = 0;
  let interval;

  function goTo(index) {
    slides.forEach(s => s.classList.remove('active'));
    indicators.forEach(i => i.classList.remove('active'));
    slides[index].classList.add('active');
    indicators[index].classList.add('active');
    current = index;
  }

  function next() {
    goTo((current + 1) % slides.length);
  }

  function startAuto() {
    if (interval) clearInterval(interval);
    interval = setInterval(next, 5000);
  }

  if (indicators.length) {
    indicators.forEach((btn, i) => {
      btn.addEventListener('click', () => {
        goTo(i);
        startAuto();
      });
    });
    startAuto();
  }
})();

// ===== 品牌信任模块切换 =====
(function() {
  const trustTabs = document.querySelectorAll('.trust-tab');
  const trustPanels = document.querySelectorAll('.trust-panel');
  if (trustTabs.length) {
    trustTabs.forEach(tab => {
      tab.addEventListener('click', function() {
        const target = this.dataset.panel;
        trustTabs.forEach(t => t.classList.remove('active'));
        trustPanels.forEach(p => p.classList.remove('active'));
        this.classList.add('active');
        const panel = document.getElementById('panel-' + target);
        if (panel) panel.classList.add('active');
      });
    });
  }
})();

// ===== 加入询价篮按钮交互 =====
(function() {
  document.querySelectorAll('.add-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      this.textContent = '已加入 ✓';
    });
  });
})();