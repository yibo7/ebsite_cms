
In.ready('vue', function () {

    var app = new Vue({
        el: '#vue_app',
        delimiters: ['[[', ']]'],  // 将绑定语法从 {{ }} 改为 [[ ]]
        data: {
            Quantity: 1,  // 购买数量
            ContentId: "",  // 商品id
            SelProduct:null, // 选中的规格
            Products:[] //规格列表
        },
        methods: {

            go_to_car: function (event) {
                if(this.Quantity<1){
                    alert('购买数量必须大于0');
                    return;
                }
                if(this.Quantity>this.SelProduct.stock){
                    alert('当前商品库存不足，购买数量不要超过库存'+this.SelProduct.stock);
                    return;
                }
                const shopping_cart_url = "/shop/cart?cid="+this.ContentId+"&pid="+this.SelProduct.productId+"&num="+this.Quantity+"&action=1";
                // console.log(shopping_cart_url);
                window.location.href = shopping_cart_url;
            },
            option_default_sel: function () {
                if (this.Products.length > 0) {
                    this.SelProduct = this.Products[0];
                }

            },
            on_gg_click: function (product) {
                this.SelProduct = product;
            }
        }
    });
    app.ContentId = ContentId;
    app.Products = products;
    app.option_default_sel();

});

 