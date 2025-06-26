
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


    // 给有子菜单的导航添加一个下拉图标
    $('#navigation li ul.submenu').parent('li').find('> a').append('<i class="fa fa-chevron-down"></i>');
    // 给某个导航菜单添加new标识
    $('#navigation li:nth-child(5)').addClass('new');
    // 设置购物车数量
//     get_web_api("ebshop_cart/GetCartCount", (resp) => {
//         if (resp.Success) {
//             $('.cart').attr('data-content', resp.Data);
//         }
//     });
//$('.cart').attr('data-content', "12");

    $("#headingOne").click(function () {
        if ($("#collapseOne").is(":visible")) {
            $("#collapseOne").slideUp();
        } else {
            $("#collapseOne").slideDown();
        }
    });

    UpdateFilterBox();

    // 以下是模板中的js
    /* 1. Scroll Up */
    $('#back-top i').on("click", function () {
        $('body,html').animate({
            scrollTop: 0
        }, 800);
        return false;
    });
    /* 2. slick Nav */
    // mobile_menu
    var menu = $('ul#navigation');
    if(menu.length){
      menu.slicknav({
        prependTo: ".mobile_menu",
        closedSymbol: '+',
        openedSymbol:'-'
      });
    };
    //3. Search Toggle
    $("#search_input_box").hide();
    $("#search_1").on("click", function () {
        $("#search_input_box").slideToggle();
        $("#search_input").focus();
    });
    $("#close_search").on("click", function () {
        $('#search_input_box').slideUp(500);
    });


});
/**
 *  小屏幕下商品筛洗程折叠状态
 */
function UpdateFilterBox() {
    var windowWidth = $(window).width();
    if (windowWidth < 768) {
        $('#headingOne button').click();
    }
}

function randomcolor() {
    var str = Math.ceil(Math.random() * 16777215).toString(16);
    if (str.length < 6) {
        str = "0" + str;
    }
    return str;
}
