In.add('vanilla-lazyload', { path:'/js/lazyload.min.js', type: 'js', charset: 'utf-8' });
 
$(function () { 
    
    //InitLazyload();//异步加载图片
    var lazyLoad = null;
    In.ready('vanilla-lazyload', function () {
        lazyLoad = new LazyLoad();
    });
    // 出如果加载图片出错，切换到另一个地址
    $('img[data-src]').on('error', function () {

        var fallbackSrc = $(this).data('src');
        fallbackSrc = fallbackSrc.replace("f.aitanqin.com", "f3.aitanqin.com");
        $(this).attr('src', fallbackSrc);
        // 可选：取消错误事件的绑定，如果担心无限循环
        $(this).off('error');
    });

    $(".rank-list span").each(function (i) {
        $(this).text(i + 1)
    });

    $("#specialList>div").click(function () {
        let url = $(this).find("a").attr("href");
        gotourl(url);
    });
   

    if ($(".nextpage").length > 0) {
        In.ready('infinitescroll', function () {
            
            let $container = $('.chords-row').infiniteScroll(
                {
                    path: '.nextpage', //下页连接的选择器
                    append: '.score-lst-box',      //你要检索的所有项目的选择器,
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
 