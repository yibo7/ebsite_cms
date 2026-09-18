/* ===================================================================
   无限滚动加载（Infinite Scroll）
   配套模板: includes/loading_more.html
   =================================================================== */
(function () {

    // 等 defer 脚本（jQuery、comm.js）加载完成后执行
    function init() {
        if (typeof $ === 'undefined' || typeof In === 'undefined') return;

        var lazyLoad = null;
        In.ready('vanilla-lazyload', function () {
            lazyLoad = new LazyLoad();
        });

        if ($(".pagination").length > 0) {
            In.ready('infinitescroll', function () {

                var $container = $('.eb-list-box').infiniteScroll(
                    {
                        path: '.next-page',         // 下页链接的选择器
                        append: '.eb-list-item',    // 追加的商品卡片选择器
                        button: '.load-more',       // 手动加载按钮
                        status: '.page-load-status',// 加载状态区域
                        checkLastPage: true         // 自动检测是否最后一页
                    }
                );

                // 隐藏传统分页（由 Infinite Scroll 接管翻页）
                $("ul.pagination").hide();

                // 到达最后一页
                $container.on('last.infiniteScroll', function (event, body, path) {
                    console.log('Last page hit on ' + path);
                });

                // 前 2 页自动滚动加载 → 之后切换为手动点击加载
                var $viewMoreButton = $('.load-more');
                var infScroll = $container.data('infiniteScroll');
                $container.on('load.infiniteScroll', onPageLoad);

                function onPageLoad() {
                    if (infScroll.loadCount == 2) {
                        $container.infiniteScroll('option', {
                            loadOnScroll: false,    // 关闭自动加载
                        });
                        $viewMoreButton.show();
                        $container.off('load.infiniteScroll', onPageLoad);
                    }
                    if (lazyLoad) lazyLoad.update();
                }

            });
        } else {
            $(".load_more_box").hide();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();