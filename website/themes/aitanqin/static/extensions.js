
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
    $(".taglist a").each(function (i) {
        this.style.color = "#" + randomcolor();
    });
    $("#btn_open_left").click(() => {
        In.ready('boostrapjs', function () { 
            var offcanvasElement = document.getElementById('offcanvasATQ'); 
            var offcanvas = new bootstrap.Offcanvas(offcanvasElement);
            offcanvas.show();
        });
    });
     
     
});
 
function randomcolor() {
    var str = Math.ceil(Math.random() * 16777215).toString(16);
    if (str.length < 6) {
        str = "0" + str;
    }
    return str;
}

// 设置 cookie
function setCookie(name, value, days = 365) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${value}; expires=${expires}; path=/`;
}

// 读取 cookie
function getCookie(name) {
  return document.cookie.split('; ').find(row => row.startsWith(name + '='))?.split('=')[1];
}

// 设置图标样式
function updateIcon(theme) {
  const icon = document.getElementById('themeIcon');
  if (theme === 'dark') {
    icon.className = 'fa fa-moon-o';
  } else {
    icon.className = 'fa fa-sun-o';
  }
}

// 切换主题
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-bs-theme') || 'light';
  const newTheme = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-bs-theme', newTheme);
  setCookie('theme', newTheme);
  updateIcon(newTheme);
}

// 页面加载时初始化
(function () {
  const saved = getCookie('theme') || 'light';
  document.documentElement.setAttribute('data-bs-theme', saved);
  updateIcon(saved);
})();