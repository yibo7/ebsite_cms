
$(function () {

    var lazyLoad = null;
    In.ready('vanilla-lazyload', function () {
        lazyLoad = new LazyLoad();
    });

    $(".rank-list span").each(function (i) {
    $(this).text(i + 1)
    });

    if ($(".pagination").length > 0) {
        In.ready('infinitescroll', function () {

            let $container = $('.eb-list-box').infiniteScroll(
                {
                    path: '.next-page', //下页连接的选择器
                    append: '.eb-list-item',      //你要检索的所有项目的选择器,
                    button: '.load-more',   //点击哪个元素加载
                    status: '.page-load-status',
                    checkLastPage: true     //检查无限滚动是否已到达最后一页
                }
            );
            //最后一页是触发
            $container.on('last.infiniteScroll', function (event, body, path) {
                console.log(`Last page hit on ${path}`);
            });
            //以下是加载2页后需要手动加载
            let $viewMoreButton = $('.load-more');
            let infScroll = $container.data('infiniteScroll');
            $container.on('load.infiniteScroll', onPageLoad);

            function onPageLoad() {
                if (infScroll.loadCount == 2) {
                    $container.infiniteScroll('option', {
                        loadOnScroll: false, //禁止自动加载
                    });
                    $viewMoreButton.show();
                    // remove event listener
                    $container.off('load.infiniteScroll', onPageLoad);
                }
                lazyLoad.update();
            }

        });
    }else {
        $(".load_more_box").hide()
    }

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
