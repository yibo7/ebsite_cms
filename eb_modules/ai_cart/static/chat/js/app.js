/* ===================================================================
   ===== 固定折扣（已废弃，按用户组定价，不再打折） =====
   =================================================================== */
const FIXED_DISCOUNT = 0;

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
   ===== 购物车面板（通过 API 读取后端购物车） =====
   =================================================================== */

/**
 * 刷新右侧购物车面板：从 API 获取最新数据并渲染
 */
function refreshQuotePanel() {
  renderQuote();
}

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
    const resp = await fetch('/ai_cart/api/quote/chat', {
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
        // 用 product_id 作为唯一 key（每个 SKU 有自己的 product_id）
        const uniqueKey = m.product_id || m.content_id || m.sku || m.title || '';
        const displaySku = m.sku || m.title || '';
        // 存入 PRODUCT_MAP，供 "添加到购物车" 按钮查找
        window.PRODUCT_MAP[uniqueKey] = {
          _id: m.id || uniqueKey,
          title: m.title || '',
          unit_price: m.unit_price || 0,
          market_price: m.market_price || 0,
          small_pic: m.small_pic || '',
          class_name: m.class_name || '',
          sku: displaySku,
          product_id: m.product_id || '',
          url: m.url || '',
          remarks: m.remarks || ''
        };
        const thumbHtml = m.small_pic
          ? `<img src="${m.small_pic}" alt="${m.title}" style="width:48px;height:48px;object-fit:cover;border-radius:8px;">`
          : '🖨️';
        matchedProducts.push({
          id: uniqueKey,
          name: m.title || '',
          unit_price: m.unit_price || 0,
          market_price: m.market_price || 0,
          qty: m.qty || 1,
          class_name: m.class_name || '',
          sku: displaySku,
          product_id: m.product_id || '',
          url: m.url || '',
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
        id: p._id, name: p.title, unit_price: p.price || 0,
        class_name: '标准', sku: p._id, icon: '🖨️'
      }))
    };
  }
  if (matchedBrand) {
    const brandProducts = PRODUCT_DB.filter(p => p.brand === matchedBrand).slice(0, 4);
    return {
      html: `<strong>${matchedBrand}</strong> 是我们主营品牌之一，以下是部分热销型号 👇`,
      products: brandProducts.map(p => ({
        id: p._id, name: p.title, unit_price: p.price || 0,
        class_name: '标准', sku: p._id, icon: '🖨️'
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
      const up = p.unit_price || 0;
      const hasPrice = up > 0;
      const dp = calcDiscountPrice(up);
      const saved = hasPrice ? up - dp : 0;
      const productUrl = p.url || '#';
      const productLinkAttrs = p.url ? `href="${p.url}" target="_blank" rel="noopener"` : `href="#" onclick="event.stopPropagation();"`;
      productsHtml += `
        <div class="chat-product">
          <a ${productLinkAttrs} class="cp-thumb-link">${p.icon}</a>
          <div class="cp-info">
            <h4><a ${productLinkAttrs} class="cp-title-link">${p.name}</a></h4>
            <div class="cp-meta">
              <span class="tag">${p.sku || p.id}</span>
              <span class="tag">${p.class_name || ''}</span>
            </div>
          </div>
          ${hasPrice ? `
          <div class="cp-price">
            <b>¥${dp.toFixed(2)}</b>
            ${saved > 0 ? `<small>¥${up.toFixed(2)}</small><span class="save">省¥${saved.toFixed(2)}</span>` : ''}
          </div>
          ` : ''}
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
   ===== 更新店铺名称（从 API 配置读取） =====
   =================================================================== */
function updateShopName(name) {
  if (!name) return;
  const shortName = name.length > 12 ? name.substring(0, 12) : name;
  const dot = name.charAt(0).toUpperCase();
  const titleEl = document.getElementById('pageTitle');
  if (titleEl) titleEl.textContent = `AI 智能询价 | ${name} - 询价系统`;
  const dotEl = document.getElementById('logoDot');
  const nameEl = document.getElementById('logoName');
  const suffixEl = document.getElementById('logoSuffix');
  if (dotEl) dotEl.textContent = dot;
  if (nameEl) nameEl.textContent = name;
  if (suffixEl) suffixEl.textContent = '';
  const headerEl = document.getElementById('chatHeaderTitle');
  if (headerEl) headerEl.innerHTML = `${shortName} 智能询价助手 <span class="ai-badge">AI</span>`;
  const descEl = document.querySelector('meta[name="description"]');
  if (descEl && !descEl.hasAttribute('data-updated')) {
    descEl.setAttribute('data-updated', '1');
    descEl.content = `${name}AI智能询价系统，对话式咨询产品报价，实时报价，一键生成报价单。`;
  }
}

/* ===================================================================
   ===== 初始化聊天 =====
   =================================================================== */
function initChatHistory() {
  // 从后端获取可配置的欢迎语与店铺名称
  fetch('/ai_cart/api/quote/welcome')
    .then(r => r.json())
    .then(data => {
      appendMessage('ai', data.welcome, null, getCurrentTime());
      // 更新页面中所有硬编码的店铺名称
      updateShopName(data.shop_name || 'Green Rich');
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
   ===== 购物车 API 操作 =====
   =================================================================== */
function addToQuote(productId, btn, qty) {
  // productId 是 PRODUCT_MAP 的 key，即 content_id
  var product = (window.PRODUCT_MAP || {})[productId];
  if (!product) {
    showToast('商品数据异常');
    return;
  }

  var cid = product._id || productId;
  var pid = product.product_id || '';
  var num = qty || 1;

  if (!pid) {
    showToast('该商品暂无可用规格，无法加入购物车');
    return;
  }

  var body = new URLSearchParams();
  body.append('cid', cid);
  body.append('pid', pid);
  body.append('num', num);

  fetch('/shop/api/cart/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString()
  })
  .then(function (r) { return r.json(); })
  .then(function (data) {
    if (data.code === 0) {
      showToast('已加入购物车');
      if (btn) { btn.classList.add('added'); btn.textContent = '✓'; }
      renderQuote();
    } else {
      showToast(data.msg || '添加失败');
    }
  })
  .catch(function () {
    showToast('网络异常，请稍后重试');
  });
}

function renderQuote() {
  fetch('/shop/api/cart/items')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var items = (data.data && data.data.items) || [];
      renderQuoteItems(items);
    })
    .catch(function () {
      renderQuoteItems([]);
    });
}

function getNextTierHint(qtyPrices, currentQty, currentPrice) {
  if (!qtyPrices || qtyPrices.length === 0) return null;
  for (var i = 0; i < qtyPrices.length; i++) {
    var tier = qtyPrices[i];
    if (currentQty >= tier.min_qty) continue;
    if (tier.price >= currentPrice) continue;
    var diff = tier.min_qty - currentQty;
    return '再买 ' + diff + ' 件可享批发价 ¥' + Number(tier.price).toFixed(2);
  }
  return null;
}

function renderQuoteItems(items) {
  var hasItems = items.length > 0;

  var itemsHtml = '';
  if (hasItems) {
    items.forEach(function (item) {
      var up = item.price || 0;
      var mp = item.market_price || 0;
      var subtotal = up * item.qty;
      var thumbHtml = item.small_pic
        ? '<img src="' + item.small_pic + '" alt="' + item.title + '" style="width:48px;height:48px;object-fit:cover;border-radius:8px;">'
        : '📦';
      var itemUrl = item.url || '';
      var thumbLink = itemUrl
        ? '<a href="' + itemUrl + '" target="_blank" rel="noopener" class="qi-thumb-link">' + thumbHtml + '</a>'
        : '<div class="qi-thumb">' + thumbHtml + '</div>';

      // 价格来源标签
      var sourceBadge = '';
      if (item.price_source && item.price_source !== '零售价') {
        sourceBadge = '<span style="display:inline-block;font-size:10px;color:#4c6fff;background:#eef2ff;padding:0 6px;border-radius:8px;font-weight:500;line-height:1.6;margin-top:2px;">' + item.price_source + '</span>';
      }

      // 阶梯价提示
      var tierHint = getNextTierHint(item.group_qty_prices, item.qty, up);
      var tierHtml = tierHint
        ? '<div style="font-size:11px;color:#e67e22;margin-top:3px;">💡 ' + tierHint + '</div>'
        : '';

      itemsHtml += [
        '<div class="quote-item">',
          thumbLink,
          '<div class="qi-info">',
            '<h4>' + (item.title || '') + '</h4>',
            '<div class="qi-meta"><span class="tag">' + (item.sku || '') + '</span></div>',
            '<div style="font-size:13px;font-weight:700;color:var(--accent);">¥' + up.toFixed(2) +
              (mp > up ? ' <small style="font-size:11px;color:#b8c0cc;text-decoration:line-through;font-weight:400;">¥' + mp.toFixed(2) + '</small>' : '') +
            '</div>',
            sourceBadge,
            tierHtml,
            '<div class="qi-qty">',
              '<button onclick="changeQuoteQty(\'' + item.product_id + '\', -1)">−</button>',
              '<input type="number" value="' + item.qty + '" min="1" max="9999" onchange="setQuoteQty(\'' + item.product_id + '\', this.value)">',
              '<button onclick="changeQuoteQty(\'' + item.product_id + '\', 1)">+</button>',
            '</div>',
          '</div>',
          '<div class="qi-right">',
            '<div class="qi-subtotal">¥' + subtotal.toFixed(2) + '<small>' + item.qty + ' 件</small></div>',
            '<button class="qi-remove" onclick="removeFromQuote(\'' + item.product_id + '\')">✕ 移除</button>',
          '</div>',
        '</div>'
      ].join('');
    });
  } else {
    itemsHtml = [
      '<div class="quote-empty">',
        '<div class="qe-icon">📋</div>',
        '<p>还没有添加商品<br>在左侧对话中咨询，AI 会自动为您推荐</p>',
      '</div>'
    ].join('');
  }

  quoteBodyDesktop.innerHTML = itemsHtml;
  quoteBodyMobile.innerHTML = itemsHtml;

  var totalCount = items.length;
  var totalQty = items.reduce(function (s, i) { return s + i.qty; }, 0);
  var totalPrice = items.reduce(function (s, i) { return s + (i.price || 0) * i.qty; }, 0);
  var totalOriginal = items.reduce(function (s, i) { return s + (i.market_price || 0) * i.qty; }, 0);
  var discountAmount = totalOriginal - totalPrice;

  document.getElementById('qfCountDesktop').textContent = totalCount;
  document.getElementById('qfQtyDesktop').textContent = totalQty;
  document.getElementById('qfOriginalDesktop').textContent = totalOriginal.toFixed(2);
  document.getElementById('qfDiscountDesktop').textContent = discountAmount > 0 ? '-¥' + discountAmount.toFixed(2) : '—';
  document.getElementById('qfTotalDesktop').textContent = '¥' + totalPrice.toFixed(2);

  document.getElementById('qfCountMobile').textContent = totalCount;
  document.getElementById('qfQtyMobile').textContent = totalQty;
  document.getElementById('qfOriginalMobile').textContent = totalOriginal.toFixed(2);
  document.getElementById('qfDiscountMobile').textContent = discountAmount > 0 ? '-¥' + discountAmount.toFixed(2) : '—';
  document.getElementById('qfTotalMobile').textContent = '¥' + totalPrice.toFixed(2);

  quoteFooterDesktop.style.display = hasItems ? 'block' : 'none';
  quoteFooterMobile.style.display = hasItems ? 'block' : 'none';

  updateBadges(totalQty);
}

function updateBadges(qty) {
  var headerBadge = document.getElementById('headerCartBadge');
  var mobileBadge = document.getElementById('mobileQuoteBadge');
  [headerBadge, mobileBadge].forEach(function (badge) {
    if (!badge) return;
    if (qty > 0) {
      badge.textContent = qty > 99 ? '99+' : qty;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  });
}

function changeQuoteQty(pid, delta) {
  fetch('/shop/api/cart/items')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var items = (data.data && data.data.items) || [];
      var item = items.find(function (i) { return i.product_id === pid; });
      if (!item) return;
      var newQty = item.qty + delta;
      if (newQty < 1) newQty = 1;
      if (newQty > 9999) newQty = 9999;
      updateCartQty(pid, newQty);
    })
    .catch(function () {});
}

function setQuoteQty(pid, val) {
  var qty = parseInt(val, 10) || 1;
  if (qty < 1) qty = 1;
  if (qty > 9999) qty = 9999;
  updateCartQty(pid, qty);
}

function updateCartQty(pid, qty) {
  var body = new URLSearchParams();
  body.append('pid', pid);
  body.append('num', qty);

  fetch('/shop/api/cart/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString()
  })
  .then(function (r) { return r.json(); })
  .then(function (data) {
    if (data.code === 0) renderQuote();
  })
  .catch(function () {});
}

function removeFromQuote(pid) {
  var body = new URLSearchParams();
  body.append('pid', pid);

  fetch('/shop/api/cart/remove', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString()
  })
  .then(function (r) { return r.json(); })
  .then(function (data) {
    if (data.code === 0) renderQuote();
  })
  .catch(function () {});
}

/* ===================================================================
   ===== 去购物车结算 =====
   =================================================================== */
function submitToCart() {
  window.location.href = '/shop/cart';
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
  // 1. 加载购物车数据并渲染右侧面板
  renderQuote();
  // 2. 初始化聊天
  initChatHistory();
}
init();