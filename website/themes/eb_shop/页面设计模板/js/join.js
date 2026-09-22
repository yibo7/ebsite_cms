/* ===================================================================
   Green Rich 金瑞治 — 加盟合作 JavaScript
   =================================================================== */

// ===== 验证码刷新（演示） =====
window.refreshCaptcha = function() {
  const chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
  let code = '';
  for (let i = 0; i < 4; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  const captchaImg = document.getElementById('captchaImg');
  if (captchaImg) {
    captchaImg.textContent = code.split('').join(' ');
  }
};