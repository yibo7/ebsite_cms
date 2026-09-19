/* ===================================================================
   ===== 固定折扣 =====
   =================================================================== */
const FIXED_DISCOUNT = 0.10;

/* ===================================================================
   ===== 会话管理（无需登录，浏览器生成 UUID） =====
   =================================================================== */
function _generateUUID() {
  // 兼容老旧浏览器的 UUID v4 生成
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}
function getSessionId() {
  let sid = localStorage.getItem('quote_session_id');
  if (!sid) {
    sid = window.crypto?.randomUUID ? crypto.randomUUID() : _generateUUID();
    localStorage.setItem('quote_session_id', sid);
  }
  return sid;
}
const SESSION_ID = getSessionId();

/* ===================================================================
   ===== 产品数据（由 API 加载） =====
   =================================================================== */
let PRODUCT_DB = [];       // 所有产品缓存
let PRODUCT_MAP = {};      // _id → product 的映射，快速查找

async function loadProducts() {
  // 不再预先加载全部产品，在 AI 回复时动态构建 PRODUCT_MAP
  PRODUCT_DB = [];
  PRODUCT_MAP = {};
  console.log('✅ 产品数据改为按需加载');
}

/* ===================================================================
   ===== 对话历史（前端维护，每次请求全量发送） =====
   =================================================================== */
let QUOTE_SESSION = [];

/* ===================================================================
   ===== 询价单状态 =====
   =================================================================== */
let quoteItems = [];

function saveQuoteItems() {
  localStorage.setItem('eb_quote_items', JSON.stringify(quoteItems));
}

function loadQuoteItems() {
  try {
    const saved = localStorage.getItem('eb_quote_items');
    if (saved) {
      quoteItems = JSON.parse(saved) || [];
      // 页面加载后渲染询价单
      if (typeof renderQuote === 'function') setTimeout(renderQuote, 0);
    }
  } catch(e) {
    quoteItems = [];
  }
}

// 页面加载时恢复询价单
loadQuoteItems();

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

async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  addMessage('user', text);
  chatInput.value = '';
  chatInput.style.height = 'auto';

  // 追加到对话历史
  QUOTE_SESSION.push({ role: 'user', content: text });

  const typingEl = addTyping();
  typingEl.querySelector('.typing').textContent = '对方正在输入......';

  try {
    const resp = await fetch('/eb_quote/api/quote/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sessionId: SESSION_ID,
        messages: QUOTE_SESSION
      })
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const result = await resp.json();
    typingEl.remove();

    const rawReply = result.reply || '已为您查询到相关信息。';
    const replyHtml = markdownToHtml(rawReply);  // 兜底：Markdown → HTML
    const matches = result.matches || [];

    // 将匹配的产品转为前端展示格式，同时构建 PRODUCT_MAP
    const matchedProducts = [];
    if (matches.length > 0) {
      if (!window.PRODUCT_MAP) window.PRODUCT_MAP = {};
      matches.forEach(m => {
        // 存入 PRODUCT_MAP，供 "添加到询价篮" 按钮查找
        window.PRODUCT_MAP[m.productId] = {
          _id: m.productId,
          title: m.title || '',
          price: m.price || 0,
          small_pic: m.small_pic || '',
          brand: m.brand || '',
          life: '标准'
        };
        const thumbHtml = m.small_pic
          ? `<img src="${m.small_pic}" alt="${m.title}" style="width:48px;height:48px;object-fit:cover;border-radius:8px;">`
          : '🖨️';
        matchedProducts.push({
          id: m.productId,
          name: m.title || '',
          price: m.price || 0,
          qty: m.qty || 1,
          life: '标准',
          type: m.brand || '',
          icon: thumbHtml
        });
      });
    }

    addMessage('ai', replyHtml, matchedProducts);
    QUOTE_SESSION.push({ role: 'assistant', content: replyHtml });

    // 不再自动加入询价单，让用户手动点击 [+]

  } catch (e) {
    typingEl.remove();
    console.error('AI 对话异常:', e);
    // 降级：使用本地规则匹配
    const fallback = generateAIReply(text);
    addMessage('ai', fallback.html, fallback.products);
    QUOTE_SESSION.push({ role: 'assistant', content: fallback.html });
  }
}

/* ===================================================================
   ===== 降级方案：AI 不可用时用规则匹配 =====
   =================================================================== */
function generateAIReply(text) {
  const t = text.toLowerCase();
  const matchedProducts = PRODUCT_DB.filter(p =>
    t.includes(p._id.toLowerCase()) ||
    t.includes(p.title.toLowerCase()) ||
    t.includes(p.model_name?.toLowerCase() || '') ||
    (p.brand && t.includes(p.brand.toLowerCase()))
  );
  const brands = ['佳能', '东芝', '柯尼卡', '京瓷', '施乐', '夏普', '理光', '三星'];
  const matchedBrand = brands.find(b => t.includes(b));
  const isOEM = /oem|odm|定制|贴牌/.test(t);
  const isBulk = /多少|批量|批发|优惠|折扣/.test(t);

  if (isOEM) {
    return {
      html: `我们支持 <strong>OEM / ODM 定制</strong>，包括：<br>
        • 品牌 LOGO 印刷<br>
        • 包装定制<br>
        • 特定型号开发<br><br>
        定制起订量通常为 <strong>500 支 / 型号</strong>。`,
      products: []
    };
  }
  if (isBulk && matchedProducts.length === 0 && !matchedBrand) {
    return {
      html: `批量采购我们提供额外优惠 🎉<br><br>请告诉我具体需要的<strong>品牌和型号</strong>。`,
      products: []
    };
  }
  if (matchedProducts.length > 0) {
    return {
      html: `为您找到 <strong>${matchedProducts.length} 款</strong>匹配的产品 👇`,
      products: matchedProducts.map(p => ({
        id: p._id, name: p.title, price: p.price || 0,
        life: '标准', type: p.brand, icon: '🖨️'
      }))
    };
  }
  if (matchedBrand) {
    const brandProducts = PRODUCT_DB.filter(p => p.brand === matchedBrand).slice(0, 4);
    return {
      html: `<strong>${matchedBrand}</strong> 是我们主营品牌之一，以下是部分热销型号 👇`,
      products: brandProducts.map(p => ({
        id: p._id, name: p.title, price: p.price || 0,
        life: '标准', type: p.brand, icon: '🖨️'
      }))
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
   ===== 消息渲染 =====
   =================================================================== */
function appendMessage(role, html, products, timeStr) {
  const msg = document.createElement('div');
  msg.className = `msg ${role}`;
  const avatar = role === 'ai' ? '🤖' : role === 'system' ? '⚙️' : '👤';
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
   ===== 初始化聊天 =====
   =================================================================== */
function initChatHistory() {
  // 从后端获取可配置的欢迎语
  fetch('/eb_quote/api/quote/welcome')
    .then(r => r.json())
    .then(data => {
      appendMessage('ai', data.welcome, null, getCurrentTime());
    })
    .catch(() => {
      // 兜底：双语欢迎语
      appendMessage('ai', `👋 <strong>Welcome / 欢迎</strong><br><br>
         <strong>English:</strong> I'm the AI quoting assistant for <strong>Green Rich</strong>. Tell me the <strong>brand and model</strong> of the copier drum you need — I'll check availability and price right away.<br><br>
         <strong>中文:</strong> 我是 <strong>Green Rich 金瑞治</strong> 的 AI 询价助手。请告诉我您需要的复印机鼓芯的<strong>品牌</strong>和<strong>型号</strong>，我会立即为您查询报价。`, null, getCurrentTime());
    });

  QUOTE_SESSION = [
    { role: 'assistant', content: 'Welcome / 欢迎！我是 Green Rich 金瑞治 的 AI 询价助手。' }
  ];

  setTimeout(() => {
    chatBody.scrollTop = chatBody.scrollHeight;
  }, 100);
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
function addToQuote(productId, btn, qty) {
  // 从 AI 回复时动态构建的 PRODUCT_MAP 查找
  let product = (window.PRODUCT_MAP || {})[productId];
  if (!product) {
    // 兜底：可能是旧版硬编码 ID
    const legacy = {
      'IR1730': { title: '佳能 IR1730 鼓芯', price: 20 },
      'IR2016': { title: '佳能 IR2016 鼓芯', price: 23 },
      'TOSHIBA-2505': { title: '东芝 2505 鼓芯', price: 26 },
    }[productId];
    if (!legacy) return;
    product = { _id: productId, title: legacy.title, price: legacy.price, life: '标准', brand: '' };
  }

  const existing = quoteItems.find(item => item.id === productId);
  const addQty = qty || 1;
  if (existing) {
    existing.qty += addQty;
    saveQuoteItems();
    showToast(`已增加 ${addQty} 支：${product.title}`);
  } else {
    quoteItems.push({
      id: productId,
      name: product.title,
      price: product.price || 0,
      qty: addQty,
      life: product.life || '标准',
      type: product.brand || '',
      icon: product.small_pic || '🖨️',
      brand: product.brand || ''
    });
    saveQuoteItems();
    showToast(`已加入询价单：${product.title}`);
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
          <div class="qi-thumb">${item.icon && (item.icon.startsWith('http') || item.icon.startsWith('/')) ? `<img src="${item.icon}" alt="${item.name}" style="width:48px;height:48px;object-fit:cover;border-radius:8px;">` : (item.icon || '🖨️')}</div>
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
  [headerBadge, mobileBadge].forEach(badge => {
    if (!badge) return;
    if (qty > 0) {
      badge.textContent = qty > 99 ? '99+' : qty;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  });
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
  saveQuoteItems();
  renderQuote();
  showToast('已从询价单移除');
}

/* ===================================================================
   ===== 生成报价单 =====
   =================================================================== */
async function submitToCart() {
  if (quoteItems.length === 0) {
    showToast('询价单为空，请先添加产品');
    return;
  }

  const items = quoteItems.map(item => ({
    content_id: item.id,
    qty: item.qty,
    title: item.name,
    price: item.price,
    spec: item.life || '',
    small_pic: item.icon || ''
  }));

  try {
    const resp = await fetch('/eb_quote/api/quote/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sessionId: SESSION_ID,
        userAccount: SESSION_ID,
        items: items,
        discount_rate: FIXED_DISCOUNT
      })
    });
    const result = await resp.json();

    if (result.code === 0 && result.url) {
      // 清除询价单
      quoteItems = [];
      saveQuoteItems();
      renderQuote();
      // 重定向到报价单页面
      window.location.href = result.url;
    } else {
      showToast(result.msg || '生成报价单失败，请稍后重试');
    }
  } catch (e) {
    console.error('生成报价单异常:', e);
    showToast('网络异常，请稍后重试');
  }
}

/* ===================================================================
   ===== 保存询价记录（异步，不影响主流程） =====
   =================================================================== */
function saveQuoteRecord() {
  if (quoteItems.length === 0) return;

  const summary = quoteItems.map(i => `${i.name}×${i.qty}支`).join(', ');
  const total = quoteItems.reduce((s, i) => s + calcDiscountPrice(i.price) * i.qty, 0);

  fetch('/eb_quote/api/quote/save_record', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sessionId: SESSION_ID,
      items: quoteItems.map(i => ({
        content_id: i.id,
        product_id: i.id,
        qty: i.qty,
        title: i.name,
        price: i.price
      })),
      summary: summary,
      total: total
    })
  }).catch(() => {}); // 静默失败，不影响用户体验
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
  const baseUrl = window.location.origin + window.location.pathname.replace('index.html', 'cart.html');
  const quoteUrl = `${baseUrl}?quote=${token}`;
  document.getElementById('quoteLink').value = quoteUrl;
  try {
    localStorage.setItem('greenrich_quote_' + token, JSON.stringify({
      token: token, discount: FIXED_DISCOUNT, items: quoteItems, createdAt: new Date().toISOString()
    }));
  } catch (e) { /* ignore */ }
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

/**
 * 简单的 Markdown → HTML 转换（兜底用）
 * 当 AI 返回的 reply 包含 Markdown 语法时自动转为 HTML
 */
function markdownToHtml(text) {
  if (!text) return '';
  // 如果已经包含 HTML 标签，说明 AI 正确输出了 HTML，直接返回
  if (/<[a-z][\s\S]*>/i.test(text)) return text;

  let html = text;

  // 代码块 ```code``` → 忽略（不常见于报价场景，但防止破坏格式）
  html = html.replace(/```[\s\S]*?```/g, '');

  // 分隔线 --- 或 *** → <hr>
  html = html.replace(/^[-*]{3,}\s*$/gm, '<hr>');

  // 无序列表 - xxx → <ul><li>xxx</li></ul>
  html = html.replace(/^(?:[-*]\s)(.+)$/gm, '<li>$1</li>');
  html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');

  // 有序列表 1. xxx → <ol><li>xxx</li></ol>
  html = html.replace(/^\d+\.\s(.+)$/gm, '<li>$1</li>');
  html = html.replace(/((?:<li>.*<\/li>\n?)+)(?!.*<li>)/g, '<ol>$1</ol>');

  // 粗体 **text** → <strong>text</strong>
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  // 斜体 *text* → <em>text</em>
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // 换行 → <br>
  html = html.replace(/\n/g, '<br>');

  // 合并连续的 <br><br> 为段落
  html = html.replace(/(<br>\s*){2,}/g, '</p><p>');
  html = html.replace(/^<br>/, '');
  html = html.replace(/<br>$/, '');
  html = '<p>' + html + '</p>';
  html = html.replace(/<p><\/p>/g, '');

  return html;
}

/* ===================================================================
   ===== 初始化 =====
   =================================================================== */
async function init() {
  // 1. 先加载产品
  await loadProducts();
  // 2. 渲染询价单
  renderQuote();
  // 3. 初始化聊天
  initChatHistory();
}
init();