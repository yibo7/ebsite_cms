(function () {
  /* ── 配置区：按需修改 ── */
  var CONFIG = {
    homeUrl:      '/',           // 首页地址
    toolbarHeight: 50,           // 工具条高度(px)
    pageLanguage: 'zh-CN',       // 文章原始语言
    langs: [
      { code: 'zh-CN', name: '中文（简体）' },
      { code: 'zh-TW', name: '中文（繁體）' },
      { code: 'en',    name: 'English' },
      { code: 'ja',    name: '日本語' },
      { code: 'ko',    name: '한국어' },
      { code: 'fr',    name: 'Français' },
      { code: 'de',    name: 'Deutsch' },
      { code: 'es',    name: 'Español' },
      { code: 'pt',    name: 'Português' },
      { code: 'ru',    name: 'Русский' },
      { code: 'ar',    name: 'العربية' },
      { code: 'hi',    name: 'हिन्दी' },
      { code: 'th',    name: 'ภาษาไทย' },
      { code: 'vi',    name: 'Tiếng Việt' },
      { code: 'id',    name: 'Bahasa Indonesia' },
    ]
  };

  var H = CONFIG.toolbarHeight;
  var currentLang = CONFIG.pageLanguage;
  var panelOpen = false;

  /* ══════════════════════════════════════
     1. 注入 CSS
  ══════════════════════════════════════ */
  var css = [
    /* 工具条 */
    '#__cms_toolbar{position:fixed;top:0;left:0;right:0;height:' + H + 'px;',
    'background:#18181b;border-bottom:1px solid rgba(255,255,255,.07);',
    'display:flex;align-items:center;justify-content:space-between;',
    'padding:0 20px;z-index:2147483647;',
    'font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;',
    'font-size:13px;box-sizing:border-box;gap:8px;',
    'box-shadow:0 1px 0 rgba(255,255,255,.04),0 4px 16px rgba(0,0,0,.4);}',

    /* body 偏移 */
    'body{margin-top:' + H + 'px!important;top:0!important;position:static!important;}',
    'body.translated-ltr,body.translated-rtl{top:0!important;position:static!important;}',

    /* 隐藏 Google Translate 原生 UI */
    '.goog-te-banner-frame,.goog-te-balloon-frame,#goog-gt-tt,.skiptranslate',
    '{display:none!important;visibility:hidden!important;height:0!important;}',
    '.goog-te-gadget{font-size:0!important;height:0!important;overflow:hidden!important;}',

    /* 布局组 */
    '.tb-group{display:flex;align-items:center;gap:2px;flex-shrink:0;}',

    /* 品牌点 */
    '.tb-dot{width:7px;height:7px;border-radius:50%;background:#e05a2b;',
    'box-shadow:0 0 6px rgba(224,90,43,.6);margin-right:10px;flex-shrink:0;}',

    /* 按钮基础 */
    '.tb-btn{display:inline-flex;align-items:center;gap:6px;padding:0 12px;height:32px;',
    'border-radius:6px;border:1px solid transparent;background:transparent;',
    'color:rgba(255,255,255,.5);font-size:13px;font-family:inherit;cursor:pointer;',
    'text-decoration:none;white-space:nowrap;letter-spacing:.01em;',
    'transition:background .15s,color .15s,border-color .15s;}',
    '.tb-btn:hover{background:rgba(255,255,255,.07);border-color:rgba(255,255,255,.1);color:rgba(255,255,255,.9);}',
    '.tb-btn:active{background:rgba(255,255,255,.11);transform:scale(.97);}',
    '.tb-btn svg{width:14px;height:14px;flex-shrink:0;}',

    /* 分隔线 */
    '.tb-divider{width:1px;height:16px;background:rgba(255,255,255,.08);margin:0 4px;flex-shrink:0;}',

    /* 翻译按钮 */
    '.tb-btn-translate{color:rgba(255,255,255,.55);border-color:rgba(255,255,255,.08);background:rgba(255,255,255,.04);}',
    '.tb-btn-translate:hover,.tb-btn-translate.active',
    '{background:rgba(66,133,244,.18);border-color:rgba(66,133,244,.35);color:#7ab3f7;}',

    /* 翻译面板 */
    '#__cms_translate_panel{position:fixed;top:' + (H + 8) + 'px;right:20px;width:230px;',
    'background:#1f1f23;border:1px solid rgba(255,255,255,.1);border-radius:10px;',
    'box-shadow:0 8px 32px rgba(0,0,0,.6),0 1px 0 rgba(255,255,255,.05) inset;',
    'z-index:2147483646;overflow:hidden;display:none;}',
    '#__cms_translate_panel.open{display:block;animation:__panelIn .15s ease;}',
    '@keyframes __panelIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}',
    '.tp-header{padding:11px 16px 9px;font-size:11px;letter-spacing:1.5px;',
    'color:rgba(255,255,255,.25);text-transform:uppercase;border-bottom:1px solid rgba(255,255,255,.06);}',
    '.tp-list{padding:6px;max-height:260px;overflow-y:auto;}',
    '.tp-list::-webkit-scrollbar{width:4px;}',
    '.tp-list::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:2px;}',
    '.tp-item{display:flex;align-items:center;gap:10px;padding:7px 10px;border-radius:6px;',
    'cursor:pointer;color:rgba(255,255,255,.6);font-size:13px;',
    'transition:background .12s,color .12s;border:none;background:transparent;',
    'width:100%;text-align:left;font-family:inherit;}',
    '.tp-item:hover{background:rgba(255,255,255,.07);color:rgba(255,255,255,.9);}',
    '.tp-item.current{background:rgba(66,133,244,.15);color:#7ab3f7;}',
    '.tp-code{font-size:11px;font-family:"SF Mono","Fira Mono",monospace;',
    'color:rgba(255,255,255,.25);min-width:30px;}',
    '.tp-item.current .tp-code{color:rgba(66,133,244,.7);}',
    '.tp-footer{padding:7px 16px;border-top:1px solid rgba(255,255,255,.06);',
    'font-size:11px;color:rgba(255,255,255,.2);display:flex;align-items:center;gap:6px;}',

    /* 进度条 */
    '#__cms_progress{position:fixed;top:' + H + 'px;left:0;height:2px;width:0%;',
    'background:linear-gradient(90deg,#e05a2b,#f5934e);z-index:2147483647;transition:width .08s linear;}',

    /* Toast */
    '#__cms_toast{position:fixed;top:' + (H + 12) + 'px;left:50%;',
    'transform:translateX(-50%) translateY(-4px);background:#27272a;',
    'border:1px solid rgba(255,255,255,.1);color:rgba(255,255,255,.85);',
    'font-family:-apple-system,"PingFang SC",sans-serif;font-size:13px;',
    'padding:7px 16px;border-radius:7px;z-index:2147483646;opacity:0;',
    'transition:opacity .18s,transform .18s;pointer-events:none;white-space:nowrap;',
    'box-shadow:0 4px 16px rgba(0,0,0,.5);}',
    '#__cms_toast.show{opacity:1;transform:translateX(-50%) translateY(0);}',

    /* 响应式 */
    '@media(max-width:520px){',
    '.tb-btn span{display:none;}',
    '.tb-btn{padding:0 9px;}',
    '#__cms_translate_panel{right:8px;left:8px;width:auto;}}',
  ].join('');

  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  /* ══════════════════════════════════════
     2. 注入 HTML 结构
  ══════════════════════════════════════ */
  function svg(path) {
    return '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4">' + path + '</svg>';
  }

  var toolbarHtml = [
    '<div id="__cms_toolbar">',
      '<div class="tb-group">',
        '<div class="tb-dot"></div>',
        '<a class="tb-btn" href="' + CONFIG.homeUrl + '">',
          svg('<path d="M2 6.5L8 2l6 4.5V14a.5.5 0 01-.5.5h-4V10h-3v4.5h-4A.5.5 0 012 14V6.5z"/>'),
          '<span>首页</span>',
        '</a>',
        '<button class="tb-btn" id="__backBtn">',
          svg('<path d="M10 3L5 8l5 5" stroke-linecap="round" stroke-linejoin="round"/>'),
          '<span>返回</span>',
        '</button>',
      '</div>',
      '<div class="tb-group">',
        '<button class="tb-btn tb-btn-translate" id="__translateBtn">',
          svg('<path d="M2 3h6M5 2v1M3.5 3C3.5 5.5 5 7.5 7 8M2 8c1 0 3.5-1 4.5-3" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 8l2.5 6M11 11h3M13.5 14L11 8" stroke-linecap="round" stroke-linejoin="round"/>'),
          '<span>翻译</span>',
        '</button>',
        '<div class="tb-divider"></div>',
        '<button class="tb-btn" id="__shareBtn">',
          svg('<circle cx="12" cy="4" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="4" cy="8" r="1.5"/><path d="M10.55 4.67L5.45 7.33M10.55 11.33L5.45 8.67" stroke-linecap="round"/>'),
          '<span>分享</span>',
        '</button>',
        '<button class="tb-btn" id="__printBtn">',
          svg('<rect x="3" y="6" width="10" height="7" rx="1"/><path d="M5 6V2.5a.5.5 0 01.5-.5h5a.5.5 0 01.5.5V6" stroke-linecap="round"/><path d="M5 11h6M5 9h4" stroke-linecap="round"/><circle cx="11.5" cy="8.5" r="0.7" fill="currentColor" stroke="none"/>'),
          '<span>打印</span>',
        '</button>',
      '</div>',
    '</div>',

    /* 翻译面板 */
    '<div id="__cms_translate_panel">',
      '<div class="tp-header">选择翻译语言</div>',
      '<div class="tp-list" id="__tp_list"></div>',
      '<div class="tp-footer">',
        '<svg width="11" height="11" viewBox="0 0 16 16" fill="none">',
          '<circle cx="8" cy="8" r="6.5" stroke="rgba(255,255,255,0.3)" stroke-width="1.5"/>',
          '<path d="M8 7v4M8 5.5v.5" stroke="rgba(255,255,255,0.3)" stroke-width="1.5" stroke-linecap="round"/>',
        '</svg>',
        '由 Google Translate 提供',
      '</div>',
    '</div>',

    '<div id="__cms_progress"></div>',
    '<div id="__cms_toast"></div>',
  ].join('');

  var wrap = document.createElement('div');
  wrap.innerHTML = toolbarHtml;
  while (wrap.firstChild) document.body.appendChild(wrap.firstChild);

  /* ══════════════════════════════════════
     3. 注入 Google Translate 脚本
  ══════════════════════════════════════ */
  var gtDiv = document.createElement('div');
  gtDiv.id = 'google_translate_element';
  gtDiv.style.display = 'none';
  document.body.appendChild(gtDiv);

  window.googleTranslateElementInit = function () {
    new google.translate.TranslateElement({
      pageLanguage: CONFIG.pageLanguage,
      autoDisplay: false
    }, 'google_translate_element');
  };

  var gtScript = document.createElement('script');
  gtScript.src = '//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
  document.body.appendChild(gtScript);

  /* ══════════════════════════════════════
     4. 构建语言列表
  ══════════════════════════════════════ */
  var listEl = document.getElementById('__tp_list');
  CONFIG.langs.forEach(function (l) {
    var btn = document.createElement('button');
    btn.className = 'tp-item' + (l.code === currentLang ? ' current' : '');
    btn.dataset.code = l.code;
    btn.innerHTML = '<span class="tp-code">' + l.code + '</span><span>' + l.name + '</span>';
    btn.addEventListener('click', function () { selectLang(l.code, l.name); });
    listEl.appendChild(btn);
  });

  /* ══════════════════════════════════════
     5. 事件绑定
  ══════════════════════════════════════ */
  document.getElementById('__backBtn').addEventListener('click', function () {
    history.back();
  });

  document.getElementById('__translateBtn').addEventListener('click', function () {
    panelOpen = !panelOpen;
    document.getElementById('__cms_translate_panel').classList.toggle('open', panelOpen);
  });

  document.getElementById('__shareBtn').addEventListener('click', function () {
    var url = window.location.href;
    var done = function () { showToast('链接已复制到剪贴板'); };
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(done);
    } else {
      var el = document.createElement('input');
      el.value = url; document.body.appendChild(el);
      el.select(); document.execCommand('copy');
      document.body.removeChild(el); done();
    }
  });

  document.getElementById('__printBtn').addEventListener('click', function () {
    window.print();
  });

  /* 点击外部关闭面板 */
  document.addEventListener('click', function (e) {
    if (!e.target.closest('#__cms_translate_panel') &&
        !e.target.closest('#__translateBtn')) {
      panelOpen = false;
      document.getElementById('__cms_translate_panel').classList.remove('open');
    }
  });

  /* ══════════════════════════════════════
     6. 切换语言
  ══════════════════════════════════════ */
  function selectLang(code, name) {
    currentLang = code;
    listEl.querySelectorAll('.tp-item').forEach(function (el) {
      el.classList.toggle('current', el.dataset.code === code);
    });
    var sel = document.querySelector('.goog-te-combo');
    if (sel) {
      sel.value = code;
      sel.dispatchEvent(new Event('change'));
    }
    var btn = document.getElementById('__translateBtn');
    if (code === CONFIG.pageLanguage) {
      btn.classList.remove('active');
      showToast('已恢复原始语言');
    } else {
      btn.classList.add('active');
      showToast('正在翻译为 ' + name);
    }
    panelOpen = false;
    document.getElementById('__cms_translate_panel').classList.remove('open');
  }

  /* ══════════════════════════════════════
     7. Toast
  ══════════════════════════════════════ */
  function showToast(msg) {
    var t = document.getElementById('__cms_toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(function () { t.classList.remove('show'); }, 2200);
  }

  /* ══════════════════════════════════════
     8. 阅读进度条
  ══════════════════════════════════════ */
  var bar = document.getElementById('__cms_progress');
  window.addEventListener('scroll', function () {
    var scrolled = window.scrollY || document.documentElement.scrollTop;
    var total = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = (total > 0 ? Math.min(100, scrolled / total * 100) : 0).toFixed(1) + '%';
  }, { passive: true });

  /* ══════════════════════════════════════
     9. 修复 Google Translate body top 偏移
  ══════════════════════════════════════ */
  function fixOffset() {
    document.body.style.setProperty('top', '0px', 'important');
    document.body.style.setProperty('position', 'static', 'important');

    new MutationObserver(function () {
      if (document.body.style.top && document.body.style.top !== '0px') {
        document.body.style.setProperty('top', '0px', 'important');
        document.body.style.setProperty('position', 'static', 'important');
      }
      var banner = document.querySelector('.goog-te-banner-frame');
      if (banner) {
        banner.style.setProperty('display', 'none', 'important');
        banner.style.setProperty('height', '0', 'important');
      }
    }).observe(document.body, { attributes: true, attributeFilter: ['style', 'class'] });
  }

  fixOffset();
  window.addEventListener('load', fixOffset);

})();