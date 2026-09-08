/**
 * 列表页隐藏 AlphaTab 播放器
 * 点击曲谱卡片上的播放按钮，只播放音频（不跳转详情页）
 * 依赖：AlphaTab 库（由模板引入）
 * 创建于：2026-06
 */
(function () {
  'use strict';

  /* =====================================================
     配置
  ===================================================== */
  var SOUNDFONT_URL = 'https://cdn.jsdelivr.net/npm/@coderline/alphatab@1.8.4/dist/soundfont/sonivox.sf2';
  var API_BASE = '';  // 走相对路径，与详情页一致

  /* =====================================================
     状态
  ===================================================== */
  var state = {
    at: null,           // AlphaTabApi 实例
    ready: false,       // 播放器就绪（SoundFont 加载完成）
    playing: false,     // 是否正在播放
    loading: false,     // 是否正在加载乐谱
    currentId: null,    // 当前播放的文章 ID
    initAttempts: 0,
    waveTimer: null,    // 波形动画定时器
    waveRaf: null       // requestAnimationFrame id
  };

  /* =====================================================
     工具函数
  ===================================================== */
  function fmtTime(ms) {
    if (!ms || ms < 0 || isNaN(ms)) ms = 0;
    var s = Math.floor(ms / 1000);
    var m = Math.floor(s / 60);
    s = s % 60;
    return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
  }

  /** 判断播放状态 */
  function isPlayingState(e) {
    try {
      if (alphaTab.synth && alphaTab.synth.PlayerState)
        return e.state === alphaTab.synth.PlayerState.Playing;
      if (alphaTab.PlayerState)
        return e.state === alphaTab.PlayerState.Playing;
    } catch (_) {}
    return String(e.state).toLowerCase().indexOf('playing') !== -1;
  }

  /** 从播放按钮的 data-tid 获取 MongoDB ObjectId */
  function getTid(btn) {
    if (!btn) return null;
    var tid = btn.getAttribute('data-tid');
    return tid || null;
  }

  /* =====================================================
     按钮图标同步
  ===================================================== */
  function syncAllButtons() {
    var btns = document.querySelectorAll('.play-btn');
    for (var i = 0; i < btns.length; i++) {
      var btn = btns[i];
      var svg = btn.querySelector('svg');
      if (!svg) continue;
      var isActive = state.playing && btn.dataset.id === String(state.currentId);
      svg.innerHTML = isActive
        ? '<path d="M6 4h4v16H6zm8 0h4v16h-4z"/>'   // 暂停图标
        : '<path d="M6 4l14 8-14 8V4z"/>';           // 播放图标
    }
  }

  /* =====================================================
     波形动画（播放时跳动）
  ===================================================== */
  /** 获取当前播放卡片中的 .wave 容器 */
  function getCurrentWave() {
    if (!state.currentId) return null;
    var btn = document.querySelector('.play-btn[data-id="' + state.currentId + '"]');
    if (!btn) return null;
    var card = btn.closest('.song-card, .song-card-link');
    if (!card) return null;
    var wave = card.querySelector('.js-wave');
    // 如果 wave 不存在或没有子元素，不动画
    if (!wave || !wave.children.length) return null;
    return wave;
  }

  /** 播放时波形跳动动画 */
  function startWave() {
    stopWave(); // 先清除之前的动画
    var wave = getCurrentWave();
    if (!wave) return;
    var bars = wave.children;
    var count = bars.length;

    // 保存原始高度以恢复
    if (!wave._origHeights) {
      wave._origHeights = [];
      for (var i = 0; i < count; i++) {
        wave._origHeights[i] = parseInt(bars[i].style.height) || 12;
      }
    }

    function animate() {
      if (!state.playing || !state.currentId) { stopWave(); return; }
      // 检查当前 wave 是否仍然在 DOM 中
      var w = getCurrentWave();
      if (!w || w !== wave) { stopWave(); return; }

      for (var i = 0; i < count; i++) {
        // 在原始高度附近随机跳动，幅度 4~10px
        var base = wave._origHeights[i];
        var delta = Math.floor(Math.random() * 8) + 2;
        bars[i].style.height = (base + delta) + 'px';
        // 播放时高亮波形
        bars[i].style.background = '#C89A3C';
      }
      state.waveRaf = requestAnimationFrame(animate);
    }

    state.waveRaf = requestAnimationFrame(animate);
  }

  /** 停止波形动画，恢复静态样式 */
  function stopWave() {
    if (state.waveRaf) {
      cancelAnimationFrame(state.waveRaf);
      state.waveRaf = null;
    }

    // 恢复所有 wave 的原始高度和颜色
    var waves = document.querySelectorAll('.js-wave');
    for (var w = 0; w < waves.length; w++) {
      var wave = waves[w];
      var bars = wave.querySelectorAll('i');
      if (wave._origHeights) {
        for (var i = 0; i < bars.length && i < wave._origHeights.length; i++) {
          bars[i].style.height = wave._origHeights[i] + 'px';
        }
      }
      for (var j = 0; j < bars.length; j++) {
        bars[j].style.background = '';
      }
    }
  }

  /* =====================================================
     初始化 AlphaTab（隐藏实例，只用于播放音频）
  ===================================================== */
  function initPlayer() {
    if (state.at) return;
    if (typeof alphaTab === 'undefined') {
      if (state.initAttempts < 30) {
        state.initAttempts++;
        setTimeout(initPlayer, 200);
      }
      return;
    }

    var container = document.getElementById('list-at');
    if (!container) return;

    var api;
    try {
      api = new alphaTab.AlphaTabApi(container, {
        importer: { encoding: 'utf-8' },
        player:  { enablePlayer: true, soundFont: SOUNDFONT_URL },
        display: { scale: 0.3, width: 400, height: 300 }
      });
    } catch (e) {
      console.error('[列表播放器] AlphaTab 初始化失败', e);
      return;
    }
    state.at = api;

    // 关闭内置滚动
    try {
      if (alphaTab.ScrollMode !== undefined && api.settings && api.settings.player) {
        api.settings.player.scrollMode = alphaTab.ScrollMode.Off;
        api.updateSettings();
      }
    } catch (_) {}

    // SoundFont 加载进度
    api.soundFontLoad.on(function (e) {
      if (e && e.total > 0) {
        // 可选的加载进度提示
      }
    });

    api.soundFontLoaded.on(function () {
      state.ready = true;
    });

    api.playerReady.on(function () {
      state.ready = true;
    });

    // 播放状态变化
    api.playerStateChanged.on(function (e) {
      state.playing = isPlayingState(e);
      state.loading = false;
      syncAllButtons();
      if (state.playing) {
        startWave();
      } else {
        stopWave();
      }
    });

    // 播放结束
    api.playerFinished.on(function () {
      state.playing = false;
      state.currentId = null;
      state.loading = false;
      syncAllButtons();
      stopWave();
    });

    // 加载出错时恢复状态
    api.error.on(function () {
      state.loading = false;
      syncAllButtons();
      stopWave();
    });
  }

  /* =====================================================
     播放 / 暂停
  ===================================================== */
  function playScore(id, btn) {
    if (!state.at || state.loading) return;

    // 点击同一首：切换播放/暂停
    if (state.currentId === id) {
      try { state.at.playPause(); } catch (_) {}
      return;
    }

    // 切换曲目
    state.currentId = id;
    state.loading = true;

    // 先停止当前播放
    stopWave();
    try { state.at.stop(); } catch (_) {}

    // 加载新乐谱
    var url = API_BASE + '/atq/api/totab?id=' + encodeURIComponent(id);
    fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.arrayBuffer();
      })
      .then(function (buf) {
        if (!state.at || state.currentId !== id) return;
        var ok = false;
        try { ok = state.at.load(new Uint8Array(buf)); } catch (_) { ok = false; }
        if (!ok) throw new Error('load() 失败');
        // 等播放器就绪后自动播放
        var tryPlay = function (attempt) {
          if (!state.at || state.currentId !== id) return;
          if (state.ready) {
            try { state.at.playPause(); } catch (_) {}
            state.loading = false;
          } else if (attempt < 50) {
            setTimeout(function () { tryPlay(attempt + 1); }, 200);
          } else {
            state.loading = false;
            syncAllButtons();
          }
        };
        // 给渲染一点时间
        setTimeout(function () { tryPlay(0); }, 400);
      })
      .catch(function (err) {
        console.error('[列表播放器] 加载乐谱失败', err);
        state.loading = false;
        state.currentId = null;
        syncAllButtons();
      });
  }

  /* =====================================================
     事件绑定（事件委托，支持分页后新出现的元素）
  ===================================================== */
  function bindEvents() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.play-btn');
      if (!btn) return;

      // 阻止链接跳转
      e.preventDefault();
      e.stopPropagation();

      var tid = getTid(btn);
      if (!tid) return;

      btn.dataset.id = tid;
      playScore(tid, btn);
    });
  }

  /* =====================================================
     启动
  ===================================================== */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initPlayer();
      bindEvents();
    });
  } else {
    initPlayer();
    bindEvents();
  }
})();