/* ===================================================================
   Green Rich 金瑞治 — 行业资讯 JavaScript
   =================================================================== */

// ===== 分页点击（演示） =====
document.querySelectorAll('.page-btn').forEach(btn => {
  btn.addEventListener('click', function() {
    if (this.disabled) return;
    if (this.textContent === '‹' || this.textContent === '›') return;
    document.querySelectorAll('.page-btn').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
  });
});