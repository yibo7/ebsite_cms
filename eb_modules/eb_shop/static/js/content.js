// ── 价格计算工具函数 ──────────────────────────────────────────
// 与后端 _calculate_final_price 保持一致的逻辑
function calculatePrice(sku, qty) {
    const candidates = [];

    // 候选 A：会员组价格（API 已按身份过滤，有 member_price 才有效）
    if (sku.member_price !== undefined && sku.member_price !== null) {
        candidates.push({ price: sku.member_price, source: '会员价' });
    }

    // 候选 B：批量阶梯价
    if (sku.qty_prices && sku.qty_prices.length > 0) {
        for (var i = 0; i < sku.qty_prices.length; i++) {
            var tier = sku.qty_prices[i];
            var minOk = qty >= tier.min_qty;
            var maxOk = (tier.max_qty === null || tier.max_qty === undefined || tier.max_qty === '') || qty <= tier.max_qty;
            if (minOk && maxOk) {
                candidates.push({
                    price: tier.price,
                    source: '阶梯价 ' + tier.min_qty + '-' + (tier.max_qty || '∞') + ' 件档'
                });
                break;
            }
        }
    }

    // 候选 C：基础零售价（始终兜底）
    candidates.push({ price: sku.marketPrice, source: '零售价' });

    // 取最低价
    var best = candidates[0];
    for (var i = 1; i < candidates.length; i++) {
        if (candidates[i].price < best.price) {
            best = candidates[i];
        }
    }

    var finalPrice = best.price;
    var finalSource = best.source;

    // 底价校验：不低于成本价
    if (finalPrice < sku.costPrice) {
        finalPrice = sku.costPrice;
        finalSource = '成本价';
    }

    return { price: finalPrice, source: finalSource };
}

// 获取"再买 X 件"的提示
function getNextTierHint(sku, qty, currentPrice) {
    if (!sku.qty_prices || sku.qty_prices.length === 0) {
        return null;
    }
    for (var i = 0; i < sku.qty_prices.length; i++) {
        var tier = sku.qty_prices[i];
        if (qty >= tier.min_qty) continue;
        if (tier.price >= currentPrice) continue;
        var diff = tier.min_qty - qty;
        return '再买 ' + diff + ' 件可享批发价 ' + Number(tier.price).toFixed(2) + ' 元';
    }
    return null;
}

// ── 价格格式化 ──────────────────────────────────────────────
function formatPrice(val) {
    var num = Number(val);
    if (isNaN(num)) return '0.00';
    return num.toFixed(2);
}

// ── Vue 应用 ──────────────────────────────────────────────
In.ready('vue', function () {

    var app = new Vue({
        el: '#vue_app',
        delimiters: ['[[', ']]'],
        data: {
            Quantity: 1,
            ContentId: '',
            SelProduct: null,
            Products: [],
            // 图片缩略图
            thumbnails: [],
            activeThumbIndex: 0,
            mainImage: '',
            // 价格数据（从 API 异步获取）
            priceRules: null,
            priceLoading: true,
            currentPrice: 0,
            priceSource: '',
            nextTierHint: null,
            priceRange: null,
            // 收藏
            isFavorited: false,
            // Toast
            toastVisible: false,
            toastMessage: '',
            toastType: '',
            toastTimer: null
        },
        computed: {
            // 选中 SKU 的库存
            selStock: function () {
                return this.SelProduct ? this.SelProduct.stock : 0;
            },
            // 最大可买数量
            maxQty: function () {
                return this.selStock || 9999;
            }
        },
        methods: {

            // ── 异步加载价格规则 ──
            fetchPrices: function () {
                var self = this;
                self.priceLoading = true;
                var url = '/shop/api/product/' + self.ContentId + '/prices';

                fetch(url)
                    .then(function (res) { return res.json(); })
                    .then(function (data) {
                        if (data.code === 0 && data.data && data.data.skus) {
                            self.priceRules = data.data.skus;
                            self.recalcAll();
                        }
                        self.priceLoading = false;
                    })
                    .catch(function (err) {
                        console.warn('获取价格规则失败:', err);
                        self.priceLoading = false;
                    });
            },

            // ── 获取当前选中 SKU 的价格规则 ──
            getCurrentSkuRule: function () {
                if (!this.priceRules || !this.SelProduct) return null;
                for (var i = 0; i < this.priceRules.length; i++) {
                    if (this.priceRules[i].sku === this.SelProduct.sku) {
                        return this.priceRules[i];
                    }
                }
                return null;
            },

            // ── 重新计算全部（当前价格 + 价格区间 + 提示） ──
            recalcAll: function () {
                this.recalcPrice();
                this.recalcPriceRange();
            },

            // ── 重新计算当前价格 ──
            recalcPrice: function () {
                var skuRule = this.getCurrentSkuRule();
                if (!skuRule) {
                    if (this.SelProduct) {
                        this.currentPrice = this.SelProduct.marketPrice || 0;
                        this.priceSource = '零售价';
                        this.nextTierHint = null;
                    }
                    return;
                }

                var result = calculatePrice(skuRule, this.Quantity);
                this.currentPrice = result.price;
                this.priceSource = result.source;
                this.nextTierHint = getNextTierHint(skuRule, this.Quantity, result.price);

                // 如果当前 SKU 有会员价，且当前价格来自零售价/阶梯价，标注会员价信息
                if (skuRule.member_price !== undefined && skuRule.member_price !== null) {
                    // member_price 已在 API 返回中，前端计算已考虑
                }
            },

            // ── 重新计算价格区间（多 SKU） ──
            recalcPriceRange: function () {
                if (!this.priceRules || this.priceRules.length <= 1) {
                    this.priceRange = null;
                    return;
                }

                var minPrice = Infinity;
                var maxPrice = -Infinity;

                for (var i = 0; i < this.priceRules.length; i++) {
                    var result = calculatePrice(this.priceRules[i], this.Quantity);
                    if (result.price < minPrice) minPrice = result.price;
                    if (result.price > maxPrice) maxPrice = result.price;
                }

                if (minPrice < maxPrice && isFinite(minPrice) && isFinite(maxPrice)) {
                    this.priceRange = { min: minPrice, max: maxPrice };
                } else {
                    this.priceRange = null;
                }
            },

            // ── 数量变化 ──
            onQtyChange: function (val) {
                var max = this.maxQty;
                if (val < 1) val = 1;
                if (val > max) val = max;
                this.Quantity = val;
                this.recalcAll();
            },
            onQtyInput: function () {
                var val = parseInt(this.Quantity, 10);
                if (isNaN(val) || val < 1) val = 1;
                var max = this.maxQty;
                if (val > max) val = max;
                this.Quantity = val;
                this.recalcAll();
            },

            // ── 缩略图 ──
            buildThumbnails: function () {
                var thumbs = [];
                for (var i = 0; i < this.Products.length; i++) {
                    var img = this.Products[i].image;
                    if (img && thumbs.indexOf(img) === -1) {
                        thumbs.push(img);
                    }
                }
                this.thumbnails = thumbs;
                if (thumbs.length > 0) {
                    this.mainImage = thumbs[0];
                    this.activeThumbIndex = 0;
                } else if (typeof defaultImage !== 'undefined' && defaultImage) {
                    this.mainImage = defaultImage;
                }
            },
            switchThumb: function (index) {
                if (index >= 0 && index < this.thumbnails.length) {
                    this.activeThumbIndex = index;
                    this.mainImage = this.thumbnails[index];
                }
            },
            syncMainImage: function () {
                // 切换 SKU 时尝试把主图切到该 SKU 图片
                if (this.SelProduct && this.SelProduct.image) {
                    var idx = this.thumbnails.indexOf(this.SelProduct.image);
                    if (idx !== -1) {
                        this.activeThumbIndex = idx;
                        this.mainImage = this.SelProduct.image;
                    } else {
                        this.thumbnails.push(this.SelProduct.image);
                        this.activeThumbIndex = this.thumbnails.length - 1;
                        this.mainImage = this.SelProduct.image;
                    }
                }
            },
            // ── 选中规格 ──
            option_default_sel: function () {
                if (this.Products.length > 0) {
                    this.SelProduct = this.Products[0];
                }
            },
            on_gg_click: function (product) {
                if (product.stock <= 0) return;
                this.SelProduct = product;
                this.Quantity = 1;
                this.syncMainImage();
                this.recalcAll();
            },

            // ── 加入购物车 ──
            go_to_car: function () {
                if (!this.SelProduct) {
                    this.showToast('请先选择商品规格', 'warning');
                    return;
                }
                if (this.Quantity < 1) {
                    this.showToast('购买数量必须大于0', 'warning');
                    return;
                }
                if (this.Quantity > this.SelProduct.stock) {
                    this.showToast('库存不足，当前最多可购买 ' + this.SelProduct.stock + ' 件', 'warning');
                    return;
                }

                // 后端会在 add_item 时重新计算价格并校验
                var url = "/shop/cart?cid=" + this.ContentId + "&pid=" + this.SelProduct.productId + "&num=" + this.Quantity + "&action=1";
                window.location.href = url;
            },

            // ── 收藏 ──
            toggleFavorite: function () {
                var self = this;
                if (typeof fav_content === 'function') {
                    fav_content(ContentId);
                }
                self.isFavorited = !self.isFavorited;
                self.showToast(self.isFavorited ? '已加入收藏' : '已取消收藏', 'success');
            },

            // ── Toast ──
            showToast: function (message, type) {
                var self = this;
                self.toastMessage = message;
                self.toastType = type || '';
                self.toastVisible = true;
                clearTimeout(self.toastTimer);
                self.toastTimer = setTimeout(function () {
                    self.toastVisible = false;
                }, 2600);
            },

            // ── 格式化价格（暴露到模板） ──
            formatPrice: function (val) {
                return formatPrice(val);
            }
        }
    });

    // 初始化数据
    app.ContentId = ContentId;
    app.Products = products || [];
    app.buildThumbnails();
    app.option_default_sel();
    if (app.SelProduct) {
        app.syncMainImage();
    }

    // 异步加载价格规则
    app.fetchPrices();

    // 检查收藏状态
    if (typeof check_fav_status === 'function') {
        check_fav_status(ContentId);
    }
});