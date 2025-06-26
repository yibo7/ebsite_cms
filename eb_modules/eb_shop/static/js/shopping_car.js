 

jQuery(function ($) {

    (function () {
        window.inputNumber = function (el) {
            var min = el.attr('min') || false;
            var max = el.attr('max') || false;
            var els = {};
            els.dec = el.prev();
            els.inc = el.next();

            el.each(function () {
                init($(this));
            });
            function init(el) {

                els.dec.on('click', decrement);
                els.inc.on('click', increment);
                function decrement() {
                    var value = el[0].value;
                    value--;
                    if (!min || value >= min) {
                        //el[0].value = value;
                        $(el[0]).val(value).trigger('change');
                    }
                }

                function increment() {
                    var value = el[0].value;
                    value++;
                    if (!max || value <= max) {
                        //el[0].value = value++;
                        $(el[0]).val(value++).trigger('change');
                    }
                }
            }
        }
    })(); 
    $('.input-number').each(function (index, element) {
        inputNumber($(element));
    });

    InitShopingCar();
});

function get_url(){
     // 创建一个URL对象
    const url = new URL(window.location.href);
    // 清除查询参数和哈希
    url.search = '';
    url.hash = '';
    // 获取干净的URL
    return url.toString();
}

function InitShopingCar() {
    $('.quantity input').change(function () {        
        if (isint(this)) {
            const ContentId = $(this).data("cid"); // 产品ID
            const ProductId = $(this).data("pid"); // SKU并非产品ID
            const iQuantity = $(this).val(); 
            const current_url = get_url();
            // 重定向
            window.location.href = current_url+"?cid="+ContentId+"&pid="+ProductId+"&num="+iQuantity+"&action=2";

        }
        else { $(this).val(1); }

    });

} 


function delcart(pid) {
   
    if (confirm("确认从购物车中移除此商品吗?")) {
        const current_url = get_url();
        window.location.href = current_url+"?action=3&pid="+pid;
    }
    
}

function clearshoppingcar() {

    if (confirm("您确认要清除购物车内所有商品吗?")) {
        const current_url = get_url();
        window.location.href = current_url+"?action=4";
    }
}
