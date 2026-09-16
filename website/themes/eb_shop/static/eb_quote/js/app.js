/* ===================================================================
   ===== 固定折扣 =====
   =================================================================== */
const FIXED_DISCOUNT = 0.10;

/* ===================================================================
   ===== 产品库 =====
   =================================================================== */
const PRODUCT_DB = [
  { id: 'IR1730', brand: '佳能', name: '佳能 IR1730 鼓芯', price: 20, life: '5万页', type: '原色/绿色', icon: '🖨️' },
  { id: 'IR1435', brand: '佳能', name: '佳能 IR1435 鼓芯', price: 20, life: '4万页', type: '原色/绿色', icon: '🖨️' },
  { id: 'IR2016', brand: '佳能', name: '佳能 IR2016 鼓芯', price: 23, life: '8万页', type: '原厂', icon: '🖨️' },
  { id: 'IR2270', brand: '佳能', name: '佳能 IR2270 鼓芯', price: 28, life: '8万页', type: '原厂', icon: '🖨️' },
  { id: 'IR2525', brand: '佳能', name: '佳能 IR2525 鼓芯', price: 28, life: '8万页', type: '原厂', icon: '🖨️' },
  { id: 'IR1018', brand: '佳能', name: '佳能 IR1018 鼓芯', price: 12, life: '3万页', type: 'OEM', icon: '🖨️' },
  { id: 'IRC5540', brand: '佳能', name: '佳能 IRC5540 鼓芯', price: 31, life: '8万页', type: '新都', icon: '🖨️' },
  { id: 'TOSHIBA-2505', brand: '东芝', name: '东芝 2505 鼓芯', price: 26, life: '6万页', type: '原厂', icon: '🖨️' },
  { id: 'TOSHIBA-3005', brand: '东芝', name: '东芝 3005 鼓芯', price: 32, life: '8万页', type: '原厂', icon: '🖨️' },
  { id: 'KONICA-C224', brand: '柯尼卡', name: '柯尼卡 C224 鼓芯', price: 45, life: '10万页', type: '原厂', icon: '🖨️' },
  { id: 'KYOCERA-TK', brand: '京瓷', name: '京瓷 TK 鼓芯', price: 38, life: '10万页', type: '原厂', icon: '🖨️' },
  { id: 'XEROX-3370', brand: '施乐', name: '施乐 3370 鼓芯', price: 42, life: '8万页', type: '原厂', icon: '🖨️' },
  { id: 'SHARP-2608', brand: '夏普', name: '夏普 2608 鼓芯', price: 35, life: '8万页', type: '原厂', icon: '🖨️' },
  { id: 'RICOH-MP2014', brand: '理光', name: '理光 MP2014 鼓芯', price: 30, life: '6万页', type: '原厂', icon: '🖨️' },
  { id: 'SAMSUNG-K2200', brand: '三星', name: '三星 K2200 鼓芯', price: 25, life: '5万页', type: 'OEM', icon: '🖨️' }
];

/* ===================================================================
   ===== 询价单状态 =====
   =================================================================== */
let quoteItems = [
  { id: 'IR1730', name: '佳能 IR1730 鼓芯', price: 20, qty: 10, life: '5万页', type: '原色/绿色', icon: '🖨️', brand: '佳能' },
  { id: 'IR2016', name: '佳能 IR2016 鼓芯', price: 23, qty: 20, life: '8万页', type: '原厂', icon: '🖨️', brand: '佳能' },
  { id: 'TOSHIBA-2505', name: '东芝 2505 鼓芯', price: 26, qty: 15, life: '6万页', type: '原厂', icon: '🖨️', brand: '东芝' }
];

/* ===================================================================
   ===== DOM 引用 =====
   =================================================================== */
const chatBody = document.getElementById('chatBody');
const chatInput = document.getElementById('chatInput');
const quoteBodyDesktop = document.getElementById('quoteBodyDesktop');
const quoteBodyMobile = document.getElementById('quoteBodyMobile');
const quoteFooterDesktop = document.getElementById('quoteFooterDesktop');
const quoteFooterMobile = document.getElementById('quoteFooterMobile');

/* ===================================================================
   ===== 原生 Offcanvas 控制 =====
   =================================================================== */
const quoteOffcanvas = document.getElementById('quoteOffcanvas');
const offcanvasBackdrop = document.getElementById('offcanvasBackdrop');

function openQuote() {
  quoteOffcanvas.classList.add('show');
  offcanvasBackdrop.classList.add('show');
  document.body.style.overflow = 'hidden';
  renderQuote();
}

function closeQuote() {
  quoteOffcanvas.classList.remove('show');
  offcanvasBackdrop.classList.remove('show');
  document.body.style.overflow = '';
}

// ESC 键关闭
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && quoteOffcanvas.classList.contains('show')) {
    closeQuote();
  }
});

/* ===================================================================
   ===== 聊天功能 =====
   =================================================================== */
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 100) + 'px';
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;
  addMessage('user', text);
  chatInput.value = '';
  chatInput.style.height = 'auto';
  const typingEl = addTyping();
  setTimeout(() => {
    typingEl.remove();
    const reply = generateAIReply(text);
    addMessage('ai', reply.html, reply.products);
  }, 800 + Math.random() * 600);
}

function appendMessage(role, html, products, timeStr) {
  const msg = document.createElement('div');
  msg.className = `msg ${role}`;
  const avatar = role === 'ai' ? '🤖' : '👤';
  const time = timeStr || getCurrentTime();

  let productsHtml = '';
  if (products && products.length > 0) {
    productsHtml = '<div class="chat-products">';
    products.forEach(p => {
      const dp = calcDiscountPrice(p.price);
      const saved = p.price - dp;
      productsHtml += `
        <div class="chat-product">
          <div class="cp-thumb">${p.icon}</div>
          <div class="cp-info">
            <h4>${p.name}</h4>
            <div class="cp-meta">
              <span class="tag">${p.id}</span>
              <span class="tag">${p.life}</span>
            </div>
          </div>
          <div class="cp-price">
            <b>¥${dp.toFixed(2)}</b>
            ${saved > 0 ? `<small>¥${p.price.toFixed(2)}</small><span class="save">省¥${saved.toFixed(2)}</span>` : ''}
          </div>
          <div class="cp-action">
            <button class="cp-add-btn" onclick="addToQuote('${p.id}', this)" title="加入询价单">+</button>
          </div>
        </div>
      `;
    });
    productsHtml += '</div>';
  }

  msg.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div>
      <div class="msg-bubble">${html}${productsHtml}</div>
      <span class="msg-time">${time}</span>
    </div>
  `;
  chatBody.appendChild(msg);
  chatBody.scrollTop = chatBody.scrollHeight;
  return msg;
}

function addMessage(role, content, products) {
  return appendMessage(role, content, products);
}

function addTyping() {
  const msg = document.createElement('div');
  msg.className = 'msg ai';
  msg.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div>
      <div class="msg-bubble">
        <div class="typing"><span></span><span></span><span></span></div>
      </div>
    </div>
  `;
  chatBody.appendChild(msg);
  chatBody.scrollTop = chatBody.scrollHeight;
  return msg;
}

function getCurrentTime() {
  const now = new Date();
  return `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
}

/* ===================================================================
   ===== 预设聊天记录 =====
   =================================================================== */
function initChatHistory() {
  appendMessage('ai', `您好！我是 <strong>Green Rich 金瑞治</strong> 的 AI 询价助手 👋<br><br>
    我可以为您实时报价复印机感光鼓芯。请告诉我您需要的<strong>品牌、型号</strong>或<strong>设备机型</strong>，我会立即为您查询。`, null, '09:12');

  appendMessage('user', '你好，我需要采购一批佳能复印机的鼓芯，型号是 IR1730，请报价。', null, '09:13');

  appendMessage('ai', `您好！<strong>佳能 IR1730 鼓芯</strong> 是我们热销型号之一。<br><br>
    已为您申请到 <strong>10% 优惠折扣</strong>，价格如下 👇<br><br>
    点击右侧 <strong>+</strong> 即可加入询价单：`, [
    PRODUCT_DB.find(p => p.id === 'IR1730')
  ], '09:13');

  appendMessage('user', '好的，先加 10 支。另外 IR2016 也帮我看看。', null, '09:14');

  appendMessage('ai', `已为您加入 <strong>佳能 IR1730 鼓芯 × 10 支</strong> ✅<br><br>
    以下是 <strong>佳能 IR2016 鼓芯</strong> 的报价，寿命 8 万页，原厂品质：`, [
    PRODUCT_DB.find(p => p.id === 'IR2016')
  ], '09:14');

  appendMessage('user', 'IR2016 也来 20 支。对了，东芝的鼓芯有推荐吗？', null, '09:15');

  appendMessage('ai', `已为您加入 <strong>佳能 IR2016 鼓芯 × 20 支</strong> ✅<br><br>
    <strong>东芝</strong> 是我们主营品牌之一，以下是两款热销型号：`, [
    PRODUCT_DB.find(p => p.id === 'TOSHIBA-2505'),
    PRODUCT_DB.find(p => p.id === 'TOSHIBA-3005')
  ], '09:15');

  appendMessage('user', '东芝 2505 来 15 支。如果我再多买一些，有额外折扣吗？', null, '09:16');

  appendMessage('ai', `已为您加入 <strong>东芝 2505 鼓芯 × 15 支</strong> ✅<br><br>
    目前您的询价单已享受 <strong>10% 优惠折扣</strong>。<br><br>
    如果单笔订单超过 <strong>5 万元</strong>，可以联系我们的销售工程师申请 <strong>额外大客户优惠</strong>。`, null, '09:16');

  appendMessage('user', '好的，我先看看。支持 OEM 定制吗？', null, '09:17');

  appendMessage('ai', `我们支持 <strong>OEM / ODM 定制</strong>，包括：<br>
    • 品牌 LOGO 印刷<br>
    • 包装定制<br>
    • 特定型号开发<br><br>
    定制起订量通常为 <strong>500 支 / 型号</strong>。您可以把需要的型号和数量告诉我，我先为您加入询价单。`, null, '09:17');

  appendMessage('user', '明白了，我先提交这批询价看看总价。', null, '09:18');

  appendMessage('ai', `好的！您当前询价单已包含 <strong>3 款产品</strong>：<br>
    • 佳能 IR1730 × 10 支<br>
    • 佳能 IR2016 × 20 支<br>
    • 东芝 2505 × 15 支<br><br>
    您可以点击右侧的 <strong>"🛒 提交到购物车"</strong> 生成正式报价单，或继续咨询其他型号。`, null, '09:18');

  setTimeout(() => {
    chatBody.scrollTop = chatBody.scrollHeight;
  }, 100);
}

/* ===================================================================
   ===== AI 回复逻辑 =====
   =================================================================== */
function generateAIReply(text) {
  const t = text.toLowerCase();
  const matchedProducts = PRODUCT_DB.filter(p =>
    t.includes(p.id.toLowerCase()) ||
    t.includes(p.name.toLowerCase()) ||
    (p.name.toLowerCase().includes(t) && t.length >= 3)
  );
  const brands = ['佳能', '东芝', '柯尼卡', '京瓷', '施乐', '夏普', '理光', '三星'];
  const matchedBrand = brands.find(b => t.includes(b));
  const isBulk = /多少|100|批量|采购|批发|优惠|折扣/.test(t);
  const isOEM = /oem|odm|定制|贴牌/.test(t);

  if (isOEM) {
    return {
      html: `我们支持 <strong>OEM / ODM 定制</strong>，包括：<br>
        • 品牌 LOGO 印刷<br>
        • 包装定制<br>
        • 特定型号开发<br><br>
        定制起订量通常为 <strong>500 支 / 型号</strong>。您可以把需要的型号和数量告诉我，我先为您加入询价单。`,
      products: []
    };
  }
  if (isBulk && matchedProducts.length === 0 && !matchedBrand) {
    return {
      html: `批量采购我们提供额外优惠 🎉<br><br>
        当前询价单已享受 <strong>10% 优惠折扣</strong>。<br><br>
        请告诉我具体需要的<strong>品牌和型号</strong>，我可以为您精准报价。`,
      products: []
    };
  }
  if (matchedProducts.length > 0) {
    return {
      html: `为您找到 <strong>${matchedProducts.length} 款</strong>匹配的产品，已按 <strong>10% 优惠折扣</strong> 报价 👇<br><br>点击右侧 <strong>+</strong> 即可加入询价单：`,
      products: matchedProducts
    };
  }
  if (matchedBrand) {
    const brandProducts = PRODUCT_DB.filter(p => p.brand === matchedBrand).slice(0, 4);
    return {
      html: `<strong>${matchedBrand}</strong> 是我们主营品牌之一，以下是部分热销型号（已按优惠折扣报价）👇<br><br>您可以告诉我具体型号，我为您精准查询。`,
      products: brandProducts
    };
  }
  return {
    html: `抱歉，我没有完全理解您的需求 😅<br><br>
      您可以尝试这样问我：<br>
      • <strong>"佳能 IR1730 多少钱？"</strong><br>
      • <strong>"东芝鼓芯有哪些型号？"</strong><br>
      • <strong>"采购 100 支有优惠吗？"</strong><br>
      • <strong>"支持 OEM 定制吗？"</strong>`,
    products: []
  };
}

/* ===================================================================
   ===== 价格计算 =====
   =================================================================== */
function calcDiscountPrice(originalPrice) {
  return originalPrice * (1 - FIXED_DISCOUNT);
}

/* ===================================================================
   ===== 询价单操作 =====
   =================================================================== */
function addToQuote(productId, btn) {
  const product = PRODUCT_DB.find(p => p.id === productId);
  if (!product) return;
  const existing = quoteItems.find(item => item.id === productId);
  if (existing) {
    existing.qty += 1;
    showToast(`已增加数量：${product.name}`);
  } else {
    quoteItems.push({
      id: product.id, name: product.name, price: product.price,
      qty: 1, life: product.life, type: product.type,
      icon: product.icon, brand: product.brand
    });
    showToast(`已加入询价单：${product.name}`);
  }
  if (btn) { btn.classList.add('added'); btn.textContent = '✓'; }
  renderQuote();
}

function renderQuote() {
  const hasItems = quoteItems.length > 0;

  let itemsHtml = '';
  if (hasItems) {
    quoteItems.forEach(item => {
      const dp = calcDiscountPrice(item.price);
      const subtotal = dp * item.qty;
      itemsHtml += `
        <div class="quote-item">
          <div class="qi-thumb">${item.icon}</div>
          <div class="qi-info">
            <h4>${item.name}</h4>
            <div class="qi-meta">
              <span class="qi-original">¥${item.price.toFixed(2)}</span>
              <span class="qi-level-price">¥${dp.toFixed(2)}</span>
            </div>
            <div class="qi-qty">
              <button onclick="changeQuoteQty('${item.id}', -1)">−</button>
              <input type="number" value="${item.qty}" min="1" max="9999" onchange="setQuoteQty('${item.id}', this.value)">
              <button onclick="changeQuoteQty('${item.id}', 1)">+</button>
            </div>
          </div>
          <div class="qi-right">
            <div class="qi-subtotal">¥${subtotal.toFixed(2)}<small>${item.qty} 支</small></div>
            <button class="qi-remove" onclick="removeFromQuote('${item.id}')">✕ 移除</button>
          </div>
        </div>
      `;
    });
  } else {
    itemsHtml = `
      <div class="quote-empty">
        <div class="qe-icon">📋</div>
        <p>还没有添加产品<br>在左侧对话中咨询，AI 会自动为您加入询价单</p>
      </div>
    `;
  }

  quoteBodyDesktop.innerHTML = itemsHtml;
  quoteBodyMobile.innerHTML = itemsHtml;

  let totalCount = quoteItems.length;
  let totalQty = quoteItems.reduce((s, i) => s + i.qty, 0);
  let originalTotal = quoteItems.reduce((s, i) => s + i.price * i.qty, 0);
  let discountTotal = quoteItems.reduce((s, i) => s + calcDiscountPrice(i.price) * i.qty, 0);
  let discountAmount = originalTotal - discountTotal;

  document.getElementById('qfCountDesktop').textContent = totalCount;
  document.getElementById('qfQtyDesktop').textContent = totalQty;
  document.getElementById('qfOriginalDesktop').textContent = formatMoney(originalTotal);
  document.getElementById('qfDiscountDesktop').textContent = `-¥${formatMoney(discountAmount)}`;
  document.getElementById('qfTotalDesktop').textContent = formatMoney(discountTotal);

  document.getElementById('qfCountMobile').textContent = totalCount;
  document.getElementById('qfQtyMobile').textContent = totalQty;
  document.getElementById('qfOriginalMobile').textContent = formatMoney(originalTotal);
  document.getElementById('qfDiscountMobile').textContent = `-¥${formatMoney(discountAmount)}`;
  document.getElementById('qfTotalMobile').textContent = formatMoney(discountTotal);

  quoteFooterDesktop.style.display = hasItems ? 'block' : 'none';
  quoteFooterMobile.style.display = hasItems ? 'block' : 'none';

  updateBadges(totalQty);
}

function updateBadges(qty) {
  const headerBadge = document.getElementById('headerCartBadge');
  const mobileBadge = document.getElementById('mobileQuoteBadge');
  if (qty > 0) {
    headerBadge.textContent = qty > 99 ? '99+' : qty;
    headerBadge.classList.remove('hidden');
    mobileBadge.textContent = qty > 99 ? '99+' : qty;
    mobileBadge.classList.remove('hidden');
  } else {
    headerBadge.classList.add('hidden');
    mobileBadge.classList.add('hidden');
  }
}

function changeQuoteQty(id, delta) {
  const item = quoteItems.find(i => i.id === id);
  if (!item) return;
  item.qty += delta;
  if (item.qty < 1) item.qty = 1;
  if (item.qty > 9999) item.qty = 9999;
  renderQuote();
}

function setQuoteQty(id, val) {
  const item = quoteItems.find(i => i.id === id);
  if (!item) return;
  let qty = parseInt(val, 10) || 1;
  if (qty < 1) qty = 1;
  if (qty > 9999) qty = 9999;
  item.qty = qty;
  renderQuote();
}

function removeFromQuote(id) {
  quoteItems = quoteItems.filter(i => i.id !== id);
  renderQuote();
  showToast('已从询价单移除');
}

/* ===================================================================
   ===== 提交到购物车 =====
   =================================================================== */
function submitToCart() {
  if (quoteItems.length === 0) {
    showToast('询价单为空，请先添加产品');
    return;
  }
  const token = 'GR' + Date.now().toString(36).toUpperCase() + Math.random().toString(36).slice(2, 6).toUpperCase();
  try {
    localStorage.setItem('greenrich_cart', JSON.stringify({
      token: token, discount: FIXED_DISCOUNT, items: quoteItems, createdAt: new Date().toISOString()
    }));
  } catch (e) { /* 忽略 */ }
  showToast('正在跳转到购物车…');
  setTimeout(() => {
    window.location.href = 'cart.html?from=ai&token=' + token;
  }, 600);
}

/* ===================================================================
   ===== 生成报价链接 =====
   =================================================================== */
function generateQuoteLink() {
  if (quoteItems.length === 0) {
    showToast('请先添加产品到询价单');
    return;
  }
  const token = 'GR' + Date.now().toString(36).toUpperCase() + Math.random().toString(36).slice(2, 6).toUpperCase();
  const baseUrl = window.location.origin + window.location.pathname.replace('ai-quote.html', 'cart.html');
  const quoteUrl = `${baseUrl}?quote=${token}`;
  document.getElementById('quoteLink').value = quoteUrl;
  try {
    localStorage.setItem('greenrich_quote_' + token, JSON.stringify({
      token: token, discount: FIXED_DISCOUNT, items: quoteItems, createdAt: new Date().toISOString()
    }));
  } catch (e) { /* 忽略 */ }
  document.getElementById('modalOverlay').classList.add('show');
}

function copyLink() {
  const input = document.getElementById('quoteLink');
  input.select();
  input.setSelectionRange(0, 99999);
  try {
    navigator.clipboard.writeText(input.value);
    showToast('链接已复制到剪贴板');
  } catch (e) {
    document.execCommand('copy');
    showToast('链接已复制');
  }
}

function closeModal() {
  document.getElementById('modalOverlay').classList.remove('show');
}

/* ===================================================================
   ===== 工具函数 =====
   =================================================================== */
function formatMoney(n) {
  return n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

let toastTimer;
function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.textContent = '✅ ' + msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2200);
}

/* ===================================================================
   ===== 初始化 =====
   =================================================================== */
function init() {
  renderQuote();
  initChatHistory();
}
init();