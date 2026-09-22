

    // ── 品牌/型号级联 ──────────────────────────────────────
    var selectedBrandId = '';   // '' = "全部"
    var selectedBrandName = '';
    var selectedModelId = '';   // '' = "全部"

    /** 渲染一条产品卡片 HTML */
    function renderProductCard(p, isFirst) {
      var badgeHtml = isFirst ? '<span class="badge hot">热销</span>' : '';
      var priceHtml = p.column_11 ? '<span class="product-price"><span class="ln">¥***</span> <small>/ 支</small></span>' : '';
      var tag3Html = p.column_3 ? '<span class="tag">' + p.column_3 + '</span>' : '';
      var tag4Html = p.column_4 ? '<span class="tag green">' + p.column_4 + '</span>' : '';
      var tag6Html = p.column_6 ? '<span class="tag gray">' + p.column_6 + '</span>' : '';
      var imgSrc = p.small_pic || '/static/images/default_product.jpg';
      var brandName = p.column_4 || '';

      return '<a href="' + p.url + '" class="product-card eb-list-item">'
        +   '<div class="product-thumb">' + badgeHtml + '<img src="' + imgSrc + '" alt="' + p.title + '"></div>'
        +   '<div class="product-body">'
        +     '<div class="product-brand">' + brandName + '</div>'
        +     '<h3>' + p.title + '</h3>'
        +     '<div class="product-tags">'
        +       tag3Html + tag4Html + tag6Html
        +     '</div>'
        +     '<div class="product-foot">'
        +       priceHtml
        +       '<div class="product-actions">'
        +         '<button class="icon-btn" title="收藏">♡</button>'
        +         '<button class="add-cart-btn" onclick="this.textContent=\'已加入 ✓\'">加入询价</button>'
        +       '</div>'
        +     '</div>'
        +   '</div>'
        + '</a>';
    }

    /** 显示筛选结果（隐藏原始列表，显示筛选列表） */
    function showFilterResult(products) {
      var serverEl = document.getElementById('serverProductList');
      var filterEl = document.getElementById('filterResultGrid');
      var pagerWrap = document.getElementById('paginationWrap');
      if (serverEl) serverEl.style.display = 'none';
      if (pagerWrap) pagerWrap.style.display = 'none';
      if (!filterEl) return;

      if (!products || products.length === 0) {
        filterEl.innerHTML = '<div class="empty-state">'
          + '<div class="empty-icon">🔍</div>'
          + '<h3>没有找到匹配的产品</h3>'
          + '<p>试试调整筛选条件，或直接联系我们获取完整产品目录。</p>'
          + '</div>';
        filterEl.style.display = '';
        updateCount(0);
        return;
      }

      var html = '';
      for (var i = 0; i < products.length; i++) {
        html += renderProductCard(products[i], i === 0);
      }
      filterEl.innerHTML = html;
      filterEl.style.display = '';
      updateCount(products.length);
    }

    /** 恢复原始服务端渲染的列表 */
    function showServerList() {
      var serverEl = document.getElementById('serverProductList');
      var filterEl = document.getElementById('filterResultGrid');
      var pagerWrap = document.getElementById('paginationWrap');
      if (serverEl) serverEl.style.display = '';
      if (filterEl) filterEl.style.display = 'none';
      if (pagerWrap) pagerWrap.style.display = '';

      var cards = document.querySelectorAll('#serverProductList .product-card');
      updateCount(cards.length);
    }

    function updateCount(n) {
      var el = document.querySelector('.result-count');
      if (el) el.textContent = '产品列表（共 ' + n + ' 件）';
    }

    // ── 品牌点击 ──────────────────────────────────────────
    function selectBrand(brandId) {
      selectedBrandId = brandId || '';
      selectedModelId = '';

      // 更新品牌标签活跃态
      var brandTags = document.querySelectorAll('#filterBrand .filter-tag');
      for (var i = 0; i < brandTags.length; i++) {
        var tag = brandTags[i];
        if (tag.getAttribute('data-id') === selectedBrandId) {
          tag.classList.add('active');
          selectedBrandName = tag.getAttribute('data-name') || tag.textContent.trim();
        } else {
          tag.classList.remove('active');
        }
      }

      if (!selectedBrandId) {
        // ── "全部" ──────────────────────────────────────
        var modelEl = document.getElementById('filterModel');
        modelEl.innerHTML = '<span class="filter-tag active" data-id="">全部</span>';
        showServerList();
        return;
      }

      // ── 某个品牌 ────────────────────────────────────
      fetch('/shop/api/product_filter?brand_name=' + encodeURIComponent(selectedBrandName))
        .then(function (r) { return r.json(); })
        .then(function (res) {
          renderModels(res.models || []);
          showFilterResult(res.products || []);
        });
    }

    // ── 型号 ──────────────────────────────────────────────
    function renderModels(models) {
      var el = document.getElementById('filterModel');
      el.innerHTML = '';
      var allBtn = document.createElement('span');
      allBtn.className = 'filter-tag active';
      allBtn.setAttribute('data-id', '');
      allBtn.textContent = '全部';
      allBtn.addEventListener('click', function () { selectModel(''); });
      el.appendChild(allBtn);

      for (var i = 0; i < models.length; i++) {
        var m = models[i];
        var span = document.createElement('span');
        span.className = 'filter-tag';
        span.setAttribute('data-id', m._id);
        span.textContent = m.name;
        span.addEventListener('click', function () { selectModel(this.getAttribute('data-id')); });
        el.appendChild(span);
      }
    }

    function selectModel(modelId) {
      selectedModelId = modelId || '';

      var modelTags = document.querySelectorAll('#filterModel .filter-tag');
      var modelName = '';
      for (var i = 0; i < modelTags.length; i++) {
        var tag = modelTags[i];
        if (tag.getAttribute('data-id') === selectedModelId) {
          tag.classList.add('active');
          modelName = tag.textContent.trim();
        } else {
          tag.classList.remove('active');
        }
      }

      var params = 'brand_name=' + encodeURIComponent(selectedBrandName);
      if (modelName && modelName !== '全部') {
        params += '&model_name=' + encodeURIComponent(modelName);
      }
      fetch('/shop/api/product_filter?' + params)
        .then(function (r) { return r.json(); })
        .then(function (res) { showFilterResult(res.products || []); });
    }

    // ── 页面初始化 ─────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function () {
      // 品牌标签由 Flask 模板渲染，只需绑定点击事件
      var brandTags = document.querySelectorAll('#filterBrand .filter-tag');
      for (var i = 0; i < brandTags.length; i++) {
        brandTags[i].addEventListener('click', function () {
          selectBrand(this.getAttribute('data-id'));
        });
      }

      // 默认显示原始服务端列表，不调用任何 API
      showServerList();
    });