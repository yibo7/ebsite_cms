
$(function () {
    $(".rank-list span").each(function (i) {
        $(this).text(i + 1)
    });
});

function setActiveNav(cid, selector = '.nav-links a', activeClass = 'active') {
    const links = document.querySelectorAll(selector);
    if (!links.length) return;

    let matched = false;

    if (cid != null && cid !== '') {
        links.forEach(el => {
            if (el.getAttribute('cid') == cid) {
                el.classList.add(activeClass);
                matched = true;
            }
        });
    }

    if (!matched) {
        links[0].classList.add(activeClass);
    }
}

// 关键：安全调用，避免 cid 未定义时报错
setActiveNav(typeof cid !== 'undefined' ? cid : '');

/* ===================================================================
   Green Rich 金瑞治 — 公共 JavaScript
   =================================================================== */

// ===== 搜索表单验证 =====
function ChkSo(ob) {
    if (ob.k.value == "") {
        alert("请输入要搜索的关键词");
        return false;
    }
}

// ===== 搜索框切换显示 =====
(function() {
  const searchToggle = document.getElementById('search-toggle');
  const searchBox = document.getElementById('search-input-box');
  const searchClose = document.getElementById('search-close');
  const searchInput = searchBox ? searchBox.querySelector('input[name="k"]') : null;

  function openSearch() {
    if (!searchBox) return;
    searchBox.classList.add('active');
    if (searchInput) {
      setTimeout(function() { searchInput.focus(); }, 100);
    }
  }

  function closeSearch() {
    if (!searchBox) return;
    searchBox.classList.remove('active');
  }

  if (searchToggle) {
    searchToggle.addEventListener('click', function(e) {
      e.preventDefault();
      if (searchBox && searchBox.classList.contains('active')) {
        closeSearch();
      } else {
        openSearch();
      }
    });
  }

  if (searchClose) {
    searchClose.addEventListener('click', function(e) {
      e.preventDefault();
      closeSearch();
    });
  }

  // 点击搜索框外部关闭
  document.addEventListener('click', function(e) {
    if (!searchBox || !searchBox.classList.contains('active')) return;
    if (!searchBox.contains(e.target) && e.target !== searchToggle && !searchToggle.contains(e.target)) {
      closeSearch();
    }
  });

  // ESC 键关闭
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && searchBox && searchBox.classList.contains('active')) {
      closeSearch();
    }
  });
})();

// ===== 移动端导航切换 =====
(function() {
  const mobileToggle = document.querySelector('.mobile-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (mobileToggle && navLinks) {
    mobileToggle.addEventListener('click', function() {
      const isFlex = navLinks.style.display === 'flex';
      navLinks.style.display = isFlex ? 'none' : 'flex';
      navLinks.style.flexDirection = 'column';
      navLinks.style.position = 'absolute';
      navLinks.style.top = '72px';
      navLinks.style.left = '0';
      navLinks.style.right = '0';
      navLinks.style.background = '#fff';
      navLinks.style.padding = '20px';
      navLinks.style.boxShadow = '0 10px 30px rgba(30,75,138,.1)';
      navLinks.style.gap = '16px';
    });
  }
})();

// ===== 平滑滚动 =====
(function() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href === '#') return;
      e.preventDefault();
      const target = document.querySelector(href);
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        const navLinks = document.querySelector('.nav-links');
        if (window.innerWidth <= 768 && navLinks) {
          navLinks.style.display = 'none';
        }
      }
    });
  });
})();
