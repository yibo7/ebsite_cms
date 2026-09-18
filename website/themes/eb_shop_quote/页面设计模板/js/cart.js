/* ===================================================================
   Green Rich 金瑞治 — 询价篮（购物车）JavaScript
   =================================================================== */

// ===== 格式化金额 =====
function formatMoney(n) {
  return n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// ===== 计算总价并更新界面 =====
function updateSummary() {
  const items = document.querySelectorAll('.cart-item');
  let selectedCount = 0;
  let totalQty = 0;
  let subtotal = 0;

  items.forEach(item => {
    const checkbox = item.querySelector('.item-select');
    if (checkbox && checkbox.checked) {
      selectedCount++;
      const price = parseFloat(item.dataset.price);
      const qty = parseInt(item.querySelector('.qty-input').value, 10) || 0;
      totalQty += qty;
      subtotal += price * qty;
    }
  });

  // 更新商品行小计
  items.forEach(item => {
    const price = parseFloat(item.dataset.price);
    const qty = parseInt(item.querySelector('.qty-input').value, 10) || 0;
    const subtotalEl = item.querySelector('.item-subtotal');
    subtotalEl.innerHTML = `¥${formatMoney(price * qty)} <small>${qty} 支</small>`;
  });

  // 更新顶部计数
  const selectedEl = document.getElementById('selectedCount');
  const totalEl = document.getElementById('totalCount');
  if (selectedEl) selectedEl.textContent = selectedCount;
  if (totalEl) totalEl.textContent = items.length;

  // 更新摘要
  const summaryCount = document.getElementById('summaryCount');
  const summaryQty = document.getElementById('summaryQty');
  const summarySubtotal = document.getElementById('summarySubtotal');
  const summaryTotal = document.getElementById('summaryTotal');
  if (summaryCount) summaryCount.textContent = selectedCount;
  if (summaryQty) summaryQty.textContent = totalQty;
  if (summarySubtotal) summarySubtotal.textContent = formatMoney(subtotal);
  if (summaryTotal) summaryTotal.textContent = formatMoney(subtotal);

  // 全选状态
  const selectAll = document.getElementById('selectAll');
  if (selectAll && items.length > 0) {
    selectAll.checked = selectedCount === items.length;
    selectAll.indeterminate = selectedCount > 0 && selectedCount < items.length;
  }

  // 空状态
  const empty = document.getElementById('cartEmpty');
  const footBar = document.getElementById('cartFootBar');
  const summary = document.getElementById('cartSummary');
  const hasItems = items.length > 0;
  if (empty) empty.style.display = hasItems ? 'none' : 'block';
  if (footBar) footBar.style.display = hasItems ? 'flex' : 'none';
  if (summary) summary.style.display = hasItems ? '' : 'none';
}

// ===== 数量增减 =====
window.changeQty = function(btn, delta) {
  const control = btn.closest('.qty-control');
  const input = control.querySelector('.qty-input');
  let val = parseInt(input.value, 10) || 1;
  val += delta;
  if (val < 1) val = 1;
  if (val > 9999) val = 9999;
  input.value = val;
  updateSummary();
};

window.updateQty = function(input) {
  let val = parseInt(input.value, 10) || 1;
  if (val < 1) val = 1;
  if (val > 9999) val = 9999;
  input.value = val;
  updateSummary();
};

// ===== 单个商品选中 =====
document.querySelectorAll('.item-select').forEach(cb => {
  cb.addEventListener('change', function() {
    const item = this.closest('.cart-item');
    if (item) item.classList.toggle('selected', this.checked);
    updateSummary();
  });
});

// ===== 全选 =====
const selectAll = document.getElementById('selectAll');
if (selectAll) {
  selectAll.addEventListener('change', function() {
    document.querySelectorAll('.item-select').forEach(cb => {
      cb.checked = this.checked;
      const item = cb.closest('.cart-item');
      if (item) item.classList.toggle('selected', this.checked);
    });
    updateSummary();
  });
}

// ===== 删除单个商品 =====
window.removeItem = function(btn) {
  const item = btn.closest('.cart-item');
  if (!item) return;
  item.style.transition = 'opacity .25s, transform .25s';
  item.style.opacity = '0';
  item.style.transform = 'translateX(-20px)';
  setTimeout(() => {
    item.remove();
    updateSummary();
    showToast('已从询价篮移除');
  }, 250);
};

// ===== 删除选中 =====
window.removeSelected = function() {
  const selected = document.querySelectorAll('.cart-item .item-select:checked');
  if (selected.length === 0) {
    showToast('请先勾选要删除的商品');
    return;
  }
  selected.forEach(cb => {
    const item = cb.closest('.cart-item');
    if (item) {
      item.style.transition = 'opacity .25s';
      item.style.opacity = '0';
      setTimeout(() => item.remove(), 250);
    }
  });
  setTimeout(() => {
    updateSummary();
    showToast(`已删除 ${selected.length} 款商品`);
  }, 280);
};

// ===== 清空询价篮 =====
window.clearCart = function() {
  const items = document.querySelectorAll('.cart-item');
  if (items.length === 0) return;
  if (!confirm('确定要清空询价篮吗？')) return;
  items.forEach(item => {
    item.style.transition = 'opacity .25s';
    item.style.opacity = '0';
    setTimeout(() => item.remove(), 250);
  });
  setTimeout(() => {
    updateSummary();
    showToast('询价篮已清空');
  }, 280);
};

// ===== 优惠码 =====
window.applyCoupon = function() {
  const code = document.getElementById('couponInput').value.trim();
  const tip = document.getElementById('couponTip');
  if (!tip) return;
  if (!code) {
    tip.textContent = '请输入优惠码';
    tip.style.color = 'var(--accent)';
    return;
  }
  tip.textContent = `优惠码「${code}」已记录，将在报价时为您核销`;
  tip.style.color = '#15803d';
  showToast('优惠码已应用');
};

// ===== 提交询价 =====
window.submitInquiry = function() {
  const selected = document.querySelectorAll('.cart-item .item-select:checked');
  if (selected.length === 0) {
    showToast('请至少勾选一款商品');
    return;
  }
  const count = document.getElementById('summaryCount').textContent;
  const total = document.getElementById('summaryTotal').textContent;
  alert(`感谢您的询价！\n\n已选商品：${count} 款\n预估合计：¥${total}\n\n我们的销售工程师将在 30 分钟内与您联系，提供正式报价单。`);
};

// ===== Toast =====
let toastTimer;
function showToast(msg) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = '✅ ' + msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2200);
}

// ===== 初始化 =====
updateSummary();