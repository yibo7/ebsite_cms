/**
 * 乐谱详情页 AlphaTab 播放器 & Vue 应用
 * 由 content.html 分离而来，通过 window.__scoreConfig 获取服务端数据
 * 依赖：Vue 3、AlphaTab（由模板引入）
 * 创建于：2026-06
 * 加载方式：defer（在 Vue 和 alphaTab 之后按序执行）
 */
(function () {
  'use strict';

  /* =====================================================
     从服务端注入的数据
  ===================================================== */
  var config = window.__scoreConfig || {};
  var tid = config.tid || '';
  // var cid = config.cid || 0;   // 未使用，暂留注释

  /* =====================================================
     配置常量
  ===================================================== */
  var API_BASE = '';   // 走相对路径 /api/atq/totab?id=tid
  var SOUNDFONT_URL = 'https://cdn.jsdelivr.net/npm/@coderline/alphatab@1.8.4/dist/soundfont/sonivox.sf2';
  var ZOOM_LEVELS = [75, 90, 100, 110, 125, 150];
  var SPEED_OPTIONS = [0.5, 0.75, 1, 1.25, 1.5];
  var PALETTE = ['#E85D26', '#3E7657', '#4A6FA5', '#C0392B', '#8E6BB5', '#C89A3C', '#2A9D8F', '#B5537A'];

  var NOTE_NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'];
  var CHORD_TEMPLATES = [
    ['', [0, 4, 7]], ['m', [0, 3, 7]], ['7', [0, 4, 7, 10]], ['maj7', [0, 4, 7, 11]],
    ['m7', [0, 3, 7, 10]], ['dim', [0, 3, 6]], ['aug', [0, 4, 8]], ['sus4', [0, 5, 7]],
    ['sus2', [0, 2, 7]], ['6', [0, 4, 7, 9]], ['m6', [0, 3, 7, 9]], ['add9', [0, 2, 4, 7]],
    ['madd9', [0, 2, 3, 7]], ['9', [0, 2, 4, 7, 10]], ['maj9', [0, 2, 4, 7, 11]],
    ['m9', [0, 2, 3, 7, 10]], ['7sus4', [0, 5, 7, 10]], ['5', [0, 7]]
  ];

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

  /* 由音级集合推断和弦名 */
  function detectChordName(pcs, bass) {
    var best = null;
    var roots = [bass];
    pcs.forEach(function (p) { if (p !== bass) roots.push(p); });
    for (var r = 0; r < roots.length; r++) {
      var root = roots[r];
      for (var t = 0; t < CHORD_TEMPLATES.length; t++) {
        var suffix = CHORD_TEMPLATES[t][0];
        var tpl = CHORD_TEMPLATES[t][1];
        var all = true;
        for (var k = 0; k < tpl.length; k++) {
          if (!pcs.has((root + tpl[k]) % 12)) { all = false; break; }
        }
        if (!all) continue;
        var extra = pcs.size - tpl.length;
        if (extra < 0 || extra > 2) continue;
        var sc = 100 - extra * 8 - (root === bass ? 0 : 12) - Math.min(tpl.length, 3);
        if (!best || sc > best.sc) best = { name: NOTE_NAMES[root] + suffix, sc: sc };
      }
    }
    return best ? best.name : null;
  }

  /* =====================================================
     Vue 应用
  ===================================================== */
  var app = Vue.createApp({
    delimiters: ['[[', ']]'],
    data: function () {
      return {
        menuOpen: false,
        favOn: false,
        subOn: false,
        authorUserId: config.authorUserId || '',
        downloadOpen: false,
        apiLoading: false,
        /* 乐谱状态 */
        phase: 'loading',            // loading | error | hidden
        overlayMsg: '正在加载乐谱…',
        fileName: '',
        fileBytes: null,
        scoreLoaded: false,
        scoreTitle: '', scoreArtist: '', scoreAlbum: '', scoreCopyright: '',
        bars: 0,
        tracks: [],
        activeTrackIdx: -1,
        chords: [],
        chordsSource: '',
        isFullscreen: false,
        /* 播放器状态 */
        playerReady: false,
        soundFontPct: 0,
        isPlaying: false,
        currentTime: 0,
        totalTime: 0,
        speed: 1,
        metronomeOn: false,
        loopOn: false,
        countInOn: false,
        volume: 80,
        heroDuration: '03:27',
        /* 显示设置 */
        layoutMode: 'page',
        zoomIdx: 2,
        zoomLevels: ZOOM_LEVELS,
        speedOptions: SPEED_OPTIONS,
      };
    },
    computed: {
      displayTitle: function () { return this.scoreLoaded && this.scoreTitle ? this.scoreTitle : '天空之城'; },
      displayArtist: function () { return this.scoreLoaded && this.scoreArtist ? this.scoreArtist : '久石让'; },
      displayAlbum: function () {
        if (this.scoreLoaded && this.scoreAlbum) return '专辑《' + this.scoreAlbum + '》';
        return '专辑《天空之城 电影原声带》';
      },
      canPlay: function () { return this.scoreLoaded && this.playerReady; },
      currentTimeText: function () { return fmtTime(this.currentTime); },
      totalTimeText: function () { return fmtTime(this.totalTime); },
      seekPct: function () {
        if (!this.totalTime || this.totalTime <= 0) return 0;
        return Math.max(0, Math.min(100, this.currentTime / this.totalTime * 100));
      },
      pbLoadingText: function () {
        if (this.playerReady) return '';
        if (this.soundFontPct < 100) return '音源加载中 ' + this.soundFontPct + '%';
        return '播放器准备中…';
      },
      quickFact: function () {
        if (this.phase === 'loading') return '正在加载乐谱…';
        if (!this.scoreLoaded) {
          return this.soundFontPct >= 100
            ? '音源已就绪 · 乐谱编号 <strong>' + tid + '</strong>'
            : '音源加载中 <strong>' + this.soundFontPct + '%</strong>';
        }
        return '《' + this.displayTitle + '》· <strong>' + this.bars + ' 小节</strong> · <strong>' + this.tracks.length + ' 音轨</strong>';
      }
    },
    methods: {
      /* ---------------- alphaTab 初始化 ---------------- */
      initAlphaTab: function () {
        var self = this;
        var container = document.getElementById('at');
        var settings = {
          importer: { encoding: 'utf-8' },
          player: { enablePlayer: true, soundFont: SOUNDFONT_URL },
          display: { scale: 1 }
        };
        try {
          this.at = new alphaTab.AlphaTabApi(container, settings);
        } catch (err) {
          this.phase = 'error';
          return;
        }
        /* 关闭内置滚动，使用自定义滚动（横向卷轴跟随光标） */
        try {
          if (alphaTab.ScrollMode !== undefined && this.at.settings && this.at.settings.player) {
            this.at.settings.player.scrollMode = alphaTab.ScrollMode.Off;
            this.at.updateSettings();
          }
        } catch (e) { /* ignore */ }

        var api = this.at;

        api.soundFontLoad.on(function (e) {
          if (e && e.total > 0) self.soundFontPct = Math.min(100, Math.floor(e.loaded / e.total * 100));
        });
        api.soundFontLoaded.on(function () { self.soundFontPct = 100; });
        api.playerReady.on(function () { self.playerReady = true; });

        api.scoreLoaded.on(function (score) { self.onScoreLoaded(score); });

        api.renderFinished.on(function () {
          if (self.scoreLoaded) { self.phase = 'hidden'; self.apiLoading = false; }
          try {
            if (api.endTime && api.endTime > 0) {
              self.totalTime = api.endTime;
              self.heroDuration = fmtTime(api.endTime);
            }
          } catch (e) { /* ignore */ }
        });

        /* 兜底：若渲染完成后容器内没有任何谱面元素，则强制重渲一次 */
        api.postRenderFinished.on(function () {
          if (!self.scoreLoaded || self._renderRetried) return;
          var main = document.getElementById('at');
          if (main && !main.querySelector('svg, canvas')) {
            self._renderRetried = true;
            setTimeout(function () { try { api.render(); } catch (e) { /* ignore */ } }, 150);
          }
        });

        api.midiLoaded.on(function (e) {
          if (e && e.endTime > 0) {
            self.totalTime = e.endTime;
            self.heroDuration = fmtTime(e.endTime);
          }
        });

        api.playerStateChanged.on(function (e) {
          self.isPlaying = self.isPlayerPlaying(e && e.state);
          if (self.isPlaying) self.startScrollLoop();
        });

        api.playerPositionChanged.on(function (e) {
          if (e && typeof e.currentTime === 'number') self.currentTime = e.currentTime;
          if (e && e.endTime > 0) self.totalTime = e.endTime;
        });

        api.playerFinished.on(function () { self.isPlaying = false; });

        api.error.on(function (err) {
          /* eslint-disable-next-line no-console */
          console.error('[alphaTab]', err);
          self.apiLoading = false;
          self.phase = 'error';
        });
      },

      isPlayerPlaying: function (state) {
        try {
          if (alphaTab.synth && alphaTab.synth.PlayerState) return state === alphaTab.synth.PlayerState.Playing;
        } catch (e) { /* ignore */ }
        try {
          if (alphaTab.PlayerState) return state === alphaTab.PlayerState.Playing;
        } catch (e) { /* ignore */ }
        return String(state).toLowerCase().indexOf('playing') !== -1;
      },

      /* ---------------- 通过乐谱 Id 请求乐谱 ---------------- */
      loadScoreFromApi: function () {
        var self = this;
        this.apiLoading = true;
        this.phase = 'loading';
        this.overlayMsg = '正在加载乐谱…';
        try { if (this.at && this.scoreLoaded) this.at.stop(); } catch (e) { /* ignore */ }
        var url = API_BASE + '/atq/api/totab?id=' + encodeURIComponent(tid);
        fetch(url).then(function (res) {
          if (!res.ok) throw new Error('HTTP ' + res.status);
          var cd = '';
          try { cd = res.headers.get('Content-Disposition') || ''; } catch (e) { /* ignore */ }
          var m = cd.match(/filename\*?="?([^";]+)"?/i);
          if (m && m[1]) self.fileName = m[1];
          return res.arrayBuffer();
        }).then(function (buf) {
          self.loadBytes(new Uint8Array(buf));
        }).catch(function () {
          self.apiLoading = false;
          self.phase = 'error';   // 仅显示「乐谱未加载」
        });
      },

      /* 加载乐谱字节（API 或本地文件通用），默认渲染第一个轨道 */
      loadBytes: function (bytes) {
        var self = this;
        if (!this.at) { this.phase = 'error'; return; }
        this.fileBytes = bytes;
        this.isPlaying = false;
        this.currentTime = 0;
        this.totalTime = 0;
        this.phase = 'loading';
        this.overlayMsg = '正在解析乐谱…';
        this._renderRetried = false;
        var ok = false;
        try { ok = this.at.load(bytes); } catch (e) { ok = false; }
        if (!ok) {
          this.apiLoading = false;
          this.phase = 'error';
        }
      },

      openLocalScore: function () {
        if (this.$refs.fileInput) this.$refs.fileInput.click();
      },

      onFilePicked: function (ev) {
        var self = this;
        var input = ev.target;
        var f = input.files && input.files[0];
        if (!f) return;
        input.value = '';
        try { if (this.at && this.scoreLoaded) this.at.stop(); } catch (e) { /* ignore */ }
        this.fileName = f.name;
        this.apiLoading = false;
        f.arrayBuffer().then(function (buf) {
          self.loadBytes(new Uint8Array(buf));
        }).catch(function () {
          self.phase = 'error';
        });
      },

      onScoreLoaded: function (score) {
        if (!score || this._score === score) return;  // renderTracks 重复触发时跳过
        this._score = score;
        this._renderRetried = false;
        this.scoreLoaded = true;
        this.apiLoading = false;
        this.scoreTitle = score.title || '';
        this.scoreArtist = score.artist || '';
        this.scoreAlbum = score.album || '';
        this.scoreCopyright = score.copyright || '';
        this.bars = score.masterBars ? score.masterBars.length : 0;

        var tracks = [];
        for (var i = 0; i < score.tracks.length; i++) {
          var t = score.tracks[i];
          tracks.push({
            idx: t.index,
            name: t.name || ('音轨 ' + (t.index + 1)),
            short: t.shortName || t.name || ('音轨 ' + (t.index + 1)),
            perc: !!t.isPercussion,
            mute: false,
            solo: false,
            color: PALETTE[i % PALETTE.length]
          });
        }
        this.tracks = tracks;
        /* 默认只渲染第一个轨道 */
        this.activeTrackIdx = tracks.length ? tracks[0].idx : -1;

        /* —— 和弦提取：优先谱内和弦标记（beat.chord），其次按小节音高分析 —— */
        var explicit = this.collectExplicitChords(score);
        if (explicit.length) {
          this.chords = explicit;
          this.chordsSource = '谱内和弦标记';
        } else {
          this.chords = this.detectChords(score);
          this.chordsSource = this.chords.length ? '按小节音高分析' : '';
        }
      },

      /* 官方数据模型：beat.hasChord / beat.chord.name（Guitar Pro 和弦图等） */
      collectExplicitChords: function (score) {
        var out = [], seen = {};
        for (var ti = 0; ti < score.tracks.length; ti++) {
          var track = score.tracks[ti];
          if (track.isPercussion) continue;
          for (var si = 0; si < track.staves.length; si++) {
            var bars = track.staves[si].bars;
            for (var bi = 0; bi < bars.length; bi++) {
              var voices = bars[bi].voices;
              for (var vi = 0; vi < voices.length; vi++) {
                var beats = voices[vi].beats;
                for (var ei = 0; ei < beats.length; ei++) {
                  var beat = beats[ei];
                  if (beat.hasChord && beat.chord && beat.chord.name) {
                    var name = String(beat.chord.name).trim();
                    if (name && !seen[name]) { seen[name] = true; out.push(name); }
                  }
                }
              }
            }
          }
        }
        return out.slice(0, 24);
      },

      /* 兜底：按小节汇总音高（适合旋律谱/分解和弦谱） */
      detectChords: function (score) {
        var out = [], seen = {};
        for (var ti = 0; ti < score.tracks.length; ti++) {
          var track = score.tracks[ti];
          if (track.isPercussion) continue;
          for (var si = 0; si < track.staves.length; si++) {
            var bars = track.staves[si].bars;
            for (var bi = 0; bi < bars.length; bi++) {
              var vals = [];
              var voices = bars[bi].voices;
              for (var vi = 0; vi < voices.length; vi++) {
                var beats = voices[vi].beats;
                for (var ei = 0; ei < beats.length; ei++) {
                  var beat = beats[ei];
                  if (beat.isEmpty || beat.isRest) continue;
                  var notes = beat.notes;
                  for (var ni = 0; ni < notes.length; ni++) {
                    var n = notes[ni];
                    if (n.isPercussion || n.isDead) continue;
                    if (n.isVisible === false) continue;
                    vals.push(n.realValue);
                  }
                }
              }
              if (vals.length < 2) continue;
              var pcs = new Set();
              var minVal = Infinity;
              for (var pi = 0; pi < vals.length; pi++) {
                pcs.add(((vals[pi] % 12) + 12) % 12);
                if (vals[pi] < minVal) minVal = vals[pi];
              }
              if (pcs.size < 2) continue;
              var bass = ((minVal % 12) + 12) % 12;
              var name = detectChordName(pcs, bass);
              if (name && !seen[name]) { seen[name] = true; out.push(name); }
            }
          }
        }
        return out.slice(0, 24);
      },

      /* ---------------- 音轨控制（切换 / 静音 / 独奏） ---------------- */
      findTrack: function (idx) {
        if (!this._score) return null;
        for (var i = 0; i < this._score.tracks.length; i++) {
          if (this._score.tracks[i].index === idx) return this._score.tracks[i];
        }
        return null;
      },

      selectTrack: function (t) {
        if (!this._score || this.activeTrackIdx === t.idx) return;
        var tr = this.findTrack(t.idx);
        if (!tr) return;
        this.activeTrackIdx = t.idx;
        try { this.at.renderTracks([tr]); } catch (e) { /* ignore */ }
      },

      toggleMute: function (t) {
        var tr = this.findTrack(t.idx);
        if (!tr) return;
        var next = !t.mute;
        try { this.at.changeTrackMute([tr], next); } catch (e) { /* ignore */ }
        t.mute = next;
        if (next && t.solo) {
          t.solo = false;
          try { this.at.changeTrackSolo([tr], false); } catch (e) { /* ignore */ }
        }
      },

      toggleSolo: function (t) {
        var tr = this.findTrack(t.idx);
        if (!tr) return;
        var next = !t.solo;
        try { this.at.changeTrackSolo([tr], next); } catch (e) { /* ignore */ }
        t.solo = next;
        if (next && t.mute) {
          t.mute = false;
          try { this.at.changeTrackMute([tr], false); } catch (e) { /* ignore */ }
        }
      },

      /* ---------------- 排版 / 缩放 / 全屏 ---------------- */
      setLayout: function (mode) {
        if (this.layoutMode === mode) return;
        this.layoutMode = mode;
        try {
          var LM = alphaTab.LayoutMode;
          this.at.settings.display.layoutMode = (mode === 'horizontal') ? LM.Horizontal : LM.Page;
          this.at.updateSettings();
          if (this.scoreLoaded) this.at.render();
        } catch (e) { /* ignore */ }
        var self = this;
        this.$nextTick(function () {
          var sc = self.$refs.scoreScroller;
          if (sc) sc.scrollLeft = 0;
        });
      },

      applyZoom: function (i) {
        if (i < 0 || i >= ZOOM_LEVELS.length) return;
        this.zoomIdx = i;
        try {
          this.at.settings.display.scale = ZOOM_LEVELS[i] / 100;
          this.at.updateSettings();
          if (this.scoreLoaded) this.at.render();
        } catch (e) { /* ignore */ }
      },
      zoomIn: function () { this.applyZoom(this.zoomIdx + 1); },
      zoomOut: function () { this.applyZoom(this.zoomIdx - 1); },

      toggleFullscreen: function () {
        this.isFullscreen = !this.isFullscreen;
        var self = this;
        this.$nextTick(function () {
          setTimeout(function () {
            var sc = self.$refs.scoreScroller;
            if (sc) { sc.scrollTop = 0; sc.scrollLeft = 0; }
            /* 尺寸变化后重新排版，保证分页 / 横向均正确铺满 */
            if (self.at && self.scoreLoaded) {
              try { self.at.render(); } catch (e) { /* ignore */ }
            }
          }, 280);
        });
      },

      /* ---------------- 打印（alphaTab 官方 A4 打印弹窗，多页完整） ---------------- */
      printScore: function () {
        if (this.at && this.scoreLoaded) {
          try { this.at.print(); return; } catch (e) { /* ignore */ }
        }
        window.print();
      },

      /* ---------------- 播放控制 ---------------- */
      togglePlay: function () {
        if (!this.canPlay) return;
        try { this.at.playPause(); } catch (e) { /* ignore */ }
      },

      restart: function () {
        if (!this.scoreLoaded) return;
        try { this.at.stop(); } catch (e) { /* ignore */ }
        this.currentTime = 0;
      },

      seekByEvent: function (ev) {
        if (!this.canPlay || !this.totalTime) return;
        var el = this.$refs.seekTrack;
        if (!el) return;
        var rect = el.getBoundingClientRect();
        var frac = (ev.clientX - rect.left) / rect.width;
        frac = Math.max(0, Math.min(1, frac));
        try { this.at.timePosition = frac * this.totalTime; } catch (e) { /* ignore */ }
        this.currentTime = frac * this.totalTime;
        this.scrollCursorIntoView(true);
      },

      setSpeed: function (v) {
        var val = parseFloat(v);
        if (isNaN(val)) return;
        this.speed = val;
        try { if (this.at) this.at.playbackSpeed = val; } catch (e) { /* ignore */ }
      },

      toggleMetronome: function () {
        this.metronomeOn = !this.metronomeOn;
        try { if (this.at) this.at.metronomeVolume = this.metronomeOn ? 0.8 : 0; } catch (e) { /* ignore */ }
      },

      toggleCountIn: function () {
        this.countInOn = !this.countInOn;
        try { if (this.at) this.at.countInVolume = this.countInOn ? 1 : 0; } catch (e) { /* ignore */ }
      },

      toggleLoop: function () {
        this.loopOn = !this.loopOn;
        try { if (this.at) this.at.isLooping = this.loopOn; } catch (e) { /* ignore */ }
      },

      setVolume: function (v) {
        this.volume = Number(v);
        try { if (this.at) this.at.masterVolume = this.volume / 100; } catch (e) { /* ignore */ }
      },

      /* ---------------- 光标跟随滚动（修复横向卷轴不滚动） ---------------- */
      startScrollLoop: function () {
        if (this._scrollRaf) return;
        var self = this;
        var loop = function () {
          if (!self.isPlaying) { self._scrollRaf = null; return; }
          self.scrollCursorIntoView(false);
          self._scrollRaf = requestAnimationFrame(loop);
        };
        this._scrollRaf = requestAnimationFrame(loop);
      },

      scrollCursorIntoView: function (instant) {
        var cursor = document.querySelector('.at-cursor-beat');
        if (!cursor || !cursor.offsetParent) return;
        if (this.layoutMode === 'horizontal') {
          var scroller = this.$refs.scoreScroller;
          if (!scroller) return;
          var cr = cursor.getBoundingClientRect();
          var sr = scroller.getBoundingClientRect();
          var cursorX = cr.left - sr.left + scroller.scrollLeft;
          var target = Math.max(0, cursorX - scroller.clientWidth * 0.32);
          var maxScroll = Math.max(0, scroller.scrollWidth - scroller.clientWidth);
          target = Math.min(target, maxScroll);
          if (instant) {
            scroller.scrollLeft = target;
          } else {
            scroller.scrollLeft += (target - scroller.scrollLeft) * 0.18;
          }
        } else {
          var now = Date.now();
          if (!instant && this._lastWinScroll && now - this._lastWinScroll < 700) return;
          var rect = cursor.getBoundingClientRect();
          var vh = window.innerHeight;
          if (rect.top < 90 || rect.bottom > vh - 130) {
            window.scrollTo({ top: window.scrollY + rect.top - vh * 0.35, behavior: instant ? 'auto' : 'smooth' });
            this._lastWinScroll = now;
          }
        }
      },

      /* ---------------- 收藏 / 订阅 ---------------- */
      doFavorite: function () {
        var self = this;
        toggleFavorite(tid, function (err, data) {
          if (err) { console.error(err); return; }
          self.favOn = data.favorited;
        });
      },

      doSubscribe: function () {
        var self = this;
        if (!self.authorUserId) return;
        toggleSubscribe(self.authorUserId, function (err, data) {
          if (err) { console.error(err); return; }
          self.subOn = data.subscribed;
        });
      },

      /* ---------------- 其他 ---------------- */
      downloadOriginal: function () {
        this.downloadOpen = false;
        if (!this.fileBytes) return;
        var blob = new Blob([this.fileBytes], { type: 'application/octet-stream' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = this.fileName || ('score_' + tid);
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
      },

      onDocClick: function (e) {
        if (this.downloadOpen && this.$refs.downloadWrap && !this.$refs.downloadWrap.contains(e.target)) {
          this.downloadOpen = false;
        }
      },

      onKeydown: function (e) {
        if (e.code === 'Escape' && this.isFullscreen) {
          this.toggleFullscreen();
          return;
        }
        if (e.code !== 'Space') return;
        var tag = (e.target && e.target.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || tag === 'button') return;
        if (!this.canPlay) return;
        e.preventDefault();
        this.togglePlay();
      }
    },
    mounted: function () {
      var self = this;
      document.addEventListener('click', this.onDocClick);
      document.addEventListener('keydown', this.onKeydown);
      this._scrollRaf = null;
      this._lastWinScroll = 0;
      this._renderRetried = false;

      /* 检查初始收藏状态（comm.js 可能尚未加载，先判断函数存在） */
      if (typeof checkFavorite === 'function') {
        checkFavorite(tid, function (err, data) {
          if (!err && data && data.favorited) self.favOn = true;
        });
      }

      /* 检查初始订阅状态 */
      if (this.authorUserId && typeof checkSubscribe === 'function') {
        checkSubscribe(this.authorUserId, function (err, data) {
          if (!err && data && data.subscribed) self.subOn = true;
        });
      }

      /* 等待容器真正可见、宽度可测量后再初始化
         （避免在 display:none / 宽度为 0 时初始化导致分页排版无法渲染） */
      var tryInit = function (attempt) {
        var el = document.getElementById('at');
        if (typeof alphaTab === 'undefined') {
          if (attempt < 50) { setTimeout(function () { tryInit(attempt + 1); }, 120); }
          else { self.phase = 'error'; }
          return;
        }
        if (el && el.clientWidth > 0) {
          self.initAlphaTab();
          self.loadScoreFromApi();   // 通过乐谱 Id 自动加载
        } else if (attempt < 50) {
          setTimeout(function () { tryInit(attempt + 1); }, 100);
        } else {
          self.initAlphaTab();       // 实在测量不到宽度也尝试初始化
          self.loadScoreFromApi();
        }
      };
      this.$nextTick(function () {
        requestAnimationFrame(function () { tryInit(0); });
      });
    }
  });
  app.mount('#app');
})();