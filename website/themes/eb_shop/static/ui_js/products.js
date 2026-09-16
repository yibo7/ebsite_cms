/* ===================================================================
   Green Rich 金瑞治 — 产品中心 JavaScript
   =================================================================== */

// ===== 筛选逻辑 =====
const productGrid = document.getElementById('productGrid');
const allProducts = Array.from(document.querySelectorAll('.product-card'));
const resultCount = document.getElementById('resultCount');
const activeFiltersEl = document.getElementById('activeFilters');
const emptyState = document.getElementById('emptyState');
const pagination = document.getElementById('pagination');

// 折叠筛选组
window.toggleFilter = function(el) {
  el.classList.toggle('collapsed');
  const list = el.nextElementSibling;
  if (list) list.classList.toggle('collapsed');
};

// 获取当前所有筛选条件
function getFilters() {
  const brands = Array.from(document.querySelectorAll('.brand-filter:checked')).map(i => i.value);
  const types = Array.from(document.querySelectorAll('.type-filter:checked')).map(i => i.value);
  const lifes = Array.from(document.querySelectorAll('.life-filter:checked')).map(i => i.value);
  const stockOnly = document.querySelector('.stock-filter:checked') !== null;

  const priceMinD = parseFloat(document.getElementById('priceMin').value) || 0;
  const priceMaxD = parseFloat(document.getElementById('priceMax').value) || Infinity;
  const priceMinM = parseFloat(document.getElementById('priceMinM').value) || 0;
  const priceMaxM = parseFloat(document.getElementById('priceMaxM').value) || Infinity;
  const priceMin = Math.max(priceMinD, priceMinM) || 0;
  const priceMax = Math.min(priceMaxD, priceMaxM) || Infinity;

  return { brands, types, lifes, stockOnly, priceMin, priceMax };
}

// 应用筛选
window.applyFilters = function() {
  const { brands, types, lifes, stockOnly, priceMin, priceMax } = getFilters();
  let visibleCount = 0;

  allProducts.forEach(card => {
    const brand = card.dataset.brand;
    const type = card.dataset.type;
    const life = parseInt(card.dataset.life, 10);
    const price = parseFloat(card.dataset.price);
    const stock = card.dataset.stock;

    let show = true;
    if (brands.length && !brands.includes(brand)) show = false;
    if (types.length && !types.includes(type)) show = false;
    if (lifes.length && !lifes.includes(String(life))) show = false;
    if (stockOnly && stock !== 'in') show = false;
    if (price < priceMin || price > priceMax) show = false;

    card.style.display = show ? '' : 'none';
    if (show) visibleCount++;
  });

  if (resultCount) resultCount.textContent = visibleCount;
  if (emptyState) emptyState.style.display = visibleCount === 0 ? 'block' : 'none';
  if (pagination) pagination.style.display = visibleCount === 0 ? 'none' : 'flex';
  renderActiveFilters();
};

// 渲染已选筛选标签
function renderActiveFilters() {
  const { brands, types, lifes, priceMin, priceMax } = getFilters();
  if (!activeFiltersEl) return;
  let html = '';
  brands.forEach(b => {
    html += `<span class="filter-chip">${b} <button onclick="removeFilter('brand','${b}')">×</button></span>`;
  });
  types.forEach(t => {
    html += `<span class="filter-chip">${t} <button onclick="removeFilter('type','${t}')">×</button></span>`;
  });
  lifes.forEach(l => {
    const label = l === '30000' ? '3万页以下' : l === '50000' ? '5万页' : '8万页';
    html += `<span class="filter-chip">${label} <button onclick="removeFilter('life','${l}')">×</button></span>`;
  });
  if (priceMin > 0 || priceMax < Infinity) {
    html += `<span class="filter-chip">¥${priceMin} - ¥${priceMax === Infinity ? '不限' : priceMax} <button onclick="removePriceFilter()">×</button></span>`;
  }
  activeFiltersEl.innerHTML = html;
}

// 移除单个筛选
window.removeFilter = function(type, value) {
  if (type === 'brand') {
    document.querySelectorAll('.brand-filter').forEach(i => { if (i.value === value) i.checked = false; });
  } else if (type === 'type') {
    document.querySelectorAll('.type-filter').forEach(i => { if (i.value === value) i.checked = false; });
  } else if (type === 'life') {
    document.querySelectorAll('.life-filter').forEach(i => { if (i.value === value) i.checked = false; });
  }
  applyFilters();
};

window.removePriceFilter = function() {
  document.getElementById('priceMin').value = '';
  document.getElementById('priceMax').value = '';
  document.getElementById('priceMinM').value = '';
  document.getElementById('priceMaxM').value = '';
  applyFilters();
};

window.applyPriceFilter = function() {
  applyFilters();
};

window.applyPriceFilterMobile = function() {
  applyFilters();
};

// 重置筛选
window.resetFilters = function() {
  document.querySelectorAll('.brand-filter, .type-filter, .life-filter, .stock-filter').forEach(i => i.checked = false);
  document.getElementById('priceMin').value = '';
  document.getElementById('priceMax').value = '';
  document.getElementById('priceMinM').value = '';
  document.getElementById('priceMaxM').value = '';
  applyFilters();
};

// 绑定筛选事件
document.querySelectorAll('.brand-filter, .type-filter, .life-filter, .stock-filter').forEach(cb => {
  cb.addEventListener('change', applyFilters);
});

// ===== 排序 =====
window.sortProducts = function() {
  const sort = document.getElementById('sortSelect').value;
  const products = Array.from(document.querySelectorAll('.product-card'));
  const container = document.getElementById('productGrid');
  products.sort((a, b) => {
    const priceA = parseFloat(a.dataset.price);
    const priceB = parseFloat(b.dataset.price);
    const lifeA = parseInt(a.dataset.life, 10);
    const lifeB = parseInt(b.dataset.life, 10);
    const newA = parseInt(a.dataset.newest, 10);
    const newB = parseInt(b.dataset.newest, 10);

    if (sort === 'price-asc') return priceA - priceB;
    if (sort === 'price-desc') return priceB - priceA;
    if (sort === 'life-desc') return lifeB - lifeA;
    if (sort === 'newest') return newA - newB;
    return newA - newB;
  });
  products.forEach(p => container.appendChild(p));
};

// ===== 分页点击 =====
document.querySelectorAll('.page-btn').forEach(btn => {
  btn.addEventListener('click', function() {
    if (this.disabled) return;
    if (this.textContent === '‹' || this.textContent === '›') return;
    document.querySelectorAll('.page-btn').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
  });
});